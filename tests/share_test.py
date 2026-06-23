#! /usr/bin/env python
# vi:ts=4:et

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import pycurl
import pytest

from . import util


def set_share_defaults(s: pycurl.CurlShare):
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_COOKIE)
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_DNS)
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_SSL_SESSION)


@pytest.fixture
def default_share() -> pycurl.CurlShare:
    s = pycurl.CurlShare()
    set_share_defaults(s)
    return s


@pytest.fixture
def default_share_no_detach() -> pycurl.CurlShare:
    s = pycurl.CurlShare(detach_on_close=False)
    set_share_defaults(s)
    return s


class WorkerThread(threading.Thread):
    def __init__(self, share: pycurl.CurlShare, url: str):
        threading.Thread.__init__(self)
        self.curl = util.DefaultCurl()
        self.curl.setopt(pycurl.URL, url + "/success")
        self.curl.setopt(pycurl.SHARE, share)
        self.sio = BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, self.sio.write)

    def run(self):
        self.curl.perform()
        self.curl.close()


def test_share(app, default_share):
    s = default_share

    t1 = WorkerThread(s, url=app)
    t2 = WorkerThread(s, url=app)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    del s

    assert t1.sio.getvalue().decode() == "success"
    assert t2.sio.getvalue().decode() == "success"


def test_share_close():
    s = pycurl.CurlShare()
    assert not s.closed
    s.close()
    assert s.closed


def test_share_close_twice():
    s = pycurl.CurlShare()
    assert not s.closed
    s.close()
    assert s.closed
    s.close()
    assert s.closed


# positional arguments are rejected
def test_positional_arguments():
    with pytest.raises(TypeError):
        pycurl.CurlShare(1)


# keyword arguments are rejected
def test_keyword_arguments():
    with pytest.raises(TypeError):
        pycurl.CurlShare(a=1)


def test_detach_on_close_keyword_argument_accepted():
    s1 = pycurl.CurlShare(detach_on_close=True)
    s2 = pycurl.CurlShare(detach_on_close=False)
    assert not s1.closed
    assert not s2.closed
    s1.close()
    s2.close()
    assert s1.closed
    assert s2.closed


def test_easy_with_share_closed_before_perform(app, default_share):
    s = default_share
    n_easies = 10
    easies = []
    for _ in range(n_easies):
        c = util.DefaultCurl()
        c.setopt(pycurl.URL, app + "/success")
        c.setopt(pycurl.SHARE, s)

        sio = BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, sio.write)

        easies.append((c, sio))

    s.close()
    assert s.closed

    for c, _ in easies:
        assert c.share() is None
        assert not c.closed


def test_easy_with_share_closed_before_perform_no_detach(app, default_share_no_detach):
    s = default_share_no_detach
    n_easies = 10
    easies = []
    for _ in range(n_easies):
        c = util.DefaultCurl()
        c.setopt(pycurl.URL, app + "/success")
        c.setopt(pycurl.SHARE, s)

        sio = BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, sio.write)

        easies.append((c, sio))

    with pytest.raises(pycurl.error):
        s.close()
    assert not s.closed

    for c, _ in easies:
        assert c.share() == s

    for c, sio in easies:
        for _ in range(3):
            sio.seek(0)
            sio.truncate(0)
            c.perform()
            assert sio.getvalue().decode() == "success"

    n = len(easies)
    q1 = n // 4
    q3 = (3 * n) // 4

    for c, _ in easies[q1:q3]:
        c.unsetopt(pycurl.SHARE)

    for c, _ in easies[:q1] + easies[q3:]:
        c.close()
        assert c.closed

    s.close()
    assert s.closed


def test_easy_set_share_closed_raises(app):
    s = pycurl.CurlShare()
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_COOKIE)
    s.close()
    assert s.closed

    c = util.DefaultCurl()
    c.setopt(pycurl.URL, app + "/success")

    with pytest.raises(pycurl.error) as excinfo:
        c.setopt(pycurl.SHARE, s)

    assert "CurlShare is closed" == str(excinfo.value)


def test_share_context_manager_detaches_by_default(app):
    c = util.DefaultCurl()
    c.setopt(pycurl.URL, app + "/success")
    sio = BytesIO()
    c.setopt(pycurl.WRITEFUNCTION, sio.write)

    with pycurl.CurlShare() as s:
        set_share_defaults(s)
        c.setopt(pycurl.SHARE, s)
        assert c.share() == s

    assert s.closed
    assert c.share() is None

    sio.seek(0)
    sio.truncate(0)
    c.perform()
    assert sio.getvalue().decode() == "success"
    c.close()


def test_share_context_manager_strict_raises_if_live_easies(app):
    c = util.DefaultCurl()
    c.setopt(pycurl.URL, app + "/success")
    sio = BytesIO()
    c.setopt(pycurl.WRITEFUNCTION, sio.write)

    with pytest.raises(pycurl.error):
        with pycurl.CurlShare(detach_on_close=False) as s:
            set_share_defaults(s)
            c.setopt(pycurl.SHARE, s)
            assert c.share() == s

    assert not s.closed
    assert c.share() == s

    c.unsetopt(pycurl.SHARE)
    s.close()
    c.close()


@pytest.fixture
def fresh_share():
    s = pycurl.CurlShare()
    yield s
    if not s.closed:
        s.close()


@pytest.mark.parametrize("method", ["share", "unshare"])
def test_zero_args_raises_type_error(fresh_share, method):
    with pytest.raises(TypeError, match="at least one LOCK_DATA"):
        getattr(fresh_share, method)()


@pytest.mark.parametrize("method", ["share", "unshare"])
@pytest.mark.parametrize(
    "bad_arg",
    [
        pytest.param([pycurl.LOCK_DATA_COOKIE], id="list"),
        pytest.param((pycurl.LOCK_DATA_COOKIE,), id="tuple"),
        pytest.param("LOCK_DATA_COOKIE", id="string"),
        pytest.param(99999, id="invalid_int"),
        pytest.param(None, id="none"),
    ],
)
def test_invalid_arg_raises_type_error(fresh_share, method, bad_arg):
    with pytest.raises(TypeError):
        getattr(fresh_share, method)(bad_arg)


@pytest.mark.parametrize("method", ["share", "unshare"])
def test_single_arg_succeeds(fresh_share, method):
    getattr(fresh_share, method)(pycurl.LOCK_DATA_COOKIE)


@pytest.mark.parametrize("method", ["share", "unshare"])
def test_multiple_args_apply(default_share, method):
    getattr(default_share, method)(
        pycurl.LOCK_DATA_COOKIE,
        pycurl.LOCK_DATA_DNS,
        pycurl.LOCK_DATA_SSL_SESSION,
    )


@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda s: s.share(pycurl.LOCK_DATA_COOKIE), id="share"),
        pytest.param(lambda s: s.unshare(pycurl.LOCK_DATA_COOKIE), id="unshare"),
        pytest.param(
            lambda s: s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_COOKIE), id="setopt"
        ),
    ],
)
def test_method_after_close_raises(call):
    s = pycurl.CurlShare()
    s.close()
    with pytest.raises(pycurl.error):
        call(s)


def test_mixed_valid_then_invalid_raises_at_invalid_item(fresh_share):
    with pytest.raises(TypeError):
        fresh_share.share(pycurl.LOCK_DATA_COOKIE, 99999)


def test_close_refuses_detach_when_easy_is_performing(app):
    s = pycurl.CurlShare()
    set_share_defaults(s)

    c = util.DefaultCurl()
    c.setopt(pycurl.URL, app + "/short_wait?delay=0.5")
    c.setopt(pycurl.SHARE, s)
    sio = BytesIO()
    c.setopt(pycurl.WRITEFUNCTION, sio.write)

    started = threading.Event()
    perform_error = []

    def run():
        started.set()
        try:
            c.perform()
        except Exception as e:
            perform_error.append(e)

    t = threading.Thread(target=run)
    t.start()
    started.wait()
    time.sleep(0.05)

    with pytest.raises(pycurl.error):
        s.close()

    t.join()
    assert not perform_error, f"perform() raised: {perform_error}"
    s.close()
    c.close()
    assert s.closed


def test_concurrent_api_calls_do_not_crash():
    s = pycurl.CurlShare()
    n_workers = 8
    iters = 200

    def worker():
        for _ in range(iters):
            s.share(pycurl.LOCK_DATA_COOKIE)
            s.unshare(pycurl.LOCK_DATA_COOKIE)
            s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_DNS)
            s.closed

    with ThreadPoolExecutor(max_workers=n_workers) as ex:
        futures = [ex.submit(worker) for _ in range(n_workers)]
        for f in futures:
            f.result()

    s.close()
