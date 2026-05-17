import time
from io import BytesIO

import pycurl
import pytest

from . import util
from .multi_driver import pump, install_timer_tracker

pytestmark = pytest.mark.skipif(
    util.pycurl_version_less_than(8, 17, 0),
    reason="libcurl < 8.17.0",
)


@pytest.fixture
def m():
    with pycurl.CurlMulti() as multi:
        yield multi


@pytest.mark.parametrize(
    "name", ["M_NOTIFYFUNCTION", "M_NOTIFY_INFO_READ", "M_NOTIFY_EASY_DONE"]
)
def test_constant_exposed_on_module_and_instance(m, name):
    assert hasattr(pycurl, name)
    assert getattr(m, name) == getattr(pycurl, name)


def test_notification_values_distinct():
    assert pycurl.M_NOTIFY_INFO_READ != pycurl.M_NOTIFY_EASY_DONE


def test_setopt_install_and_unset(m):
    m.setopt(pycurl.M_NOTIFYFUNCTION, lambda *_: None)
    m.setopt(pycurl.M_NOTIFYFUNCTION, None)


def test_notify_methods_accept_single_and_varargs(m):
    m.notify_enable(pycurl.M_NOTIFY_INFO_READ)
    m.notify_disable(pycurl.M_NOTIFY_INFO_READ)
    m.notify_enable(pycurl.M_NOTIFY_INFO_READ, pycurl.M_NOTIFY_EASY_DONE)
    m.notify_disable(pycurl.M_NOTIFY_EASY_DONE, pycurl.M_NOTIFY_INFO_READ)


@pytest.mark.parametrize("op", ["notify_enable", "notify_disable"])
def test_notify_methods_zero_args_raise(m, op):
    with pytest.raises(TypeError, match="at least one notification"):
        getattr(m, op)()


def test_notify_enable_bogus_value_raises_pycurl_error(m):
    with pytest.raises(pycurl.error):
        m.notify_enable(99999)


def _drive(multi, timer_state, observed, deadline_s=10.0):
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        pump(multi, timer_state, timeout=0.2)
        if any(n == pycurl.M_NOTIFY_EASY_DONE for n, _ in observed):
            return
    pytest.fail(f"transfer did not finish within {deadline_s}s")


@pytest.fixture
def notify_setup(app):
    with pycurl.CurlMulti(close_handles=True) as multi, util.DefaultCurl() as easy:
        easy.setopt(pycurl.URL, f"{app}/success")
        easy.setopt(pycurl.WRITEFUNCTION, BytesIO().write)
        multi.setopt(pycurl.M_SOCKETFUNCTION, lambda *_: None)
        timer_state = install_timer_tracker(multi)
        yield easy, multi, [], timer_state


def test_realistic_transfer_observes_notifications(notify_setup):
    easy, multi, observed, timer_state = notify_setup

    def on_notify(notification, curl):
        observed.append((notification, curl))

    multi.setopt(pycurl.M_NOTIFYFUNCTION, on_notify)
    multi.notify_enable(pycurl.M_NOTIFY_INFO_READ, pycurl.M_NOTIFY_EASY_DONE)
    multi.add_handle(easy)

    _drive(multi, timer_state, observed)

    notifications = [n for n, _ in observed]
    assert pycurl.M_NOTIFY_INFO_READ in notifications
    assert pycurl.M_NOTIFY_EASY_DONE in notifications

    for _, curl in observed:
        assert curl is None or curl is easy


def test_info_read_from_inside_callback(notify_setup):
    easy, multi, observed, timer_state = notify_setup
    drained = []

    def on_notify(notification, curl):
        observed.append((notification, curl))
        if notification == pycurl.M_NOTIFY_INFO_READ:
            queued, ok, err = multi.info_read()
            drained.append((queued, list(ok), list(err)))

    multi.setopt(pycurl.M_NOTIFYFUNCTION, on_notify)
    multi.notify_enable(pycurl.M_NOTIFY_INFO_READ, pycurl.M_NOTIFY_EASY_DONE)
    multi.add_handle(easy)

    _drive(multi, timer_state, observed)

    assert drained
    flat_ok = [c for _, ok, _ in drained for c in ok]
    assert easy in flat_ok


def test_callback_exception_printed_to_stderr(notify_setup, capfd):
    easy, multi, observed, timer_state = notify_setup

    def on_notify(notification, curl):
        observed.append((notification, curl))
        raise RuntimeError("boom from notify cb")

    multi.setopt(pycurl.M_NOTIFYFUNCTION, on_notify)
    multi.notify_enable(pycurl.M_NOTIFY_EASY_DONE)
    multi.add_handle(easy)

    _drive(multi, timer_state, observed)

    captured = capfd.readouterr()
    assert "boom from notify cb" in captured.err
