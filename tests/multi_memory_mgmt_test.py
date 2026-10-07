import gc
import sys
import weakref

import pycurl
import pytest

from . import util


_MULTI_CALLBACKS = [
    pytest.param(pycurl.M_SOCKETFUNCTION, id="M_SOCKETFUNCTION"),
    pytest.param(pycurl.M_TIMERFUNCTION, id="M_TIMERFUNCTION"),
    pytest.param(
        getattr(pycurl, "M_NOTIFYFUNCTION", None),
        marks=pytest.mark.skipif(
            util.pycurl_version_less_than(8, 17, 0),
            reason="libcurl < 8.17.0",
        ),
        id="M_NOTIFYFUNCTION",
    ),
]


@pytest.mark.parametrize("callback", _MULTI_CALLBACKS)
def test_callback_released_on_close(callback):
    def cb(x):
        return True

    ref = weakref.ref(cb)

    m = pycurl.CurlMulti()
    m.setopt(callback, cb)
    del cb
    assert ref() is not None, "C extension should still hold the callback"

    del m
    gc.collect()
    assert ref() is None, "callback should be released after handle is destroyed"


@pytest.mark.parametrize("callback", _MULTI_CALLBACKS)
def test_callback_reassignment_releases_old(callback):
    def first_cb(x):
        return True

    m = pycurl.CurlMulti()
    m.setopt(callback, first_cb)
    refcount_before = sys.getrefcount(first_cb)

    def second_cb(x):
        return False

    m.setopt(callback, second_cb)
    refcount_after = sys.getrefcount(first_cb)

    assert refcount_after == refcount_before - 1, "old callback not released"

    del m
    gc.collect()


def test_curl_kept_alive_while_added_to_multi():
    c = util.DefaultCurl()
    m = pycurl.CurlMulti()

    ref = weakref.ref(c)
    m.add_handle(c)
    del c

    assert ref() is not None
    gc.collect()
    assert ref() is not None

    m.remove_handle(ref())
    gc.collect()
    assert ref() is None


def _driven_multi(app, socket_callback, multi_class=pycurl.CurlMulti):
    easy = pycurl.Curl()
    easy.setopt(pycurl.URL, f"{app}/success")
    multi = multi_class()
    multi.setopt(pycurl.M_SOCKETFUNCTION, socket_callback)
    multi.add_handle(easy)
    for _ in range(3):
        multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
    return multi, easy


def test_socket_callback_invoked_during_multi_finalize(app):
    events = []
    tearing_down = False

    def socket_callback(event, fd, multi, data):
        if tearing_down:
            events.append(event)

    multi, easy = _driven_multi(app, socket_callback)

    tearing_down = True
    del multi
    gc.collect()

    assert set(events) == {pycurl.POLL_REMOVE}
    easy.close()


def test_socket_callback_not_invoked_when_del_skips_super(app):
    events = []
    tearing_down = False

    def socket_callback(event, fd, multi, data):
        if tearing_down:
            events.append(event)

    class MyMulti(pycurl.CurlMulti):
        def __del__(self):
            pass

    multi, easy = _driven_multi(app, socket_callback, MyMulti)

    tearing_down = True
    del multi
    gc.collect()

    assert events == []
    easy.close()


def test_multi_callback_cycle_is_collectable(app, unraisable):
    class Client:
        def __init__(self):
            self.seen = []
            self.multi = pycurl.CurlMulti()
            self.multi.setopt(pycurl.M_TIMERFUNCTION, self.on_timer)
            self.multi.setopt(pycurl.M_SOCKETFUNCTION, self.on_socket)
            self.easy = pycurl.Curl()
            self.easy.setopt(pycurl.URL, f"{app}/success")
            self.multi.add_handle(self.easy)
            for _ in range(3):
                self.multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)

        def on_timer(self, timeout_ms):
            self.seen.append(("timer", self.easy is not None))

        def on_socket(self, event, fd, multi, data):
            self.seen.append(("socket", self.easy is not None))

    client = Client()
    client_ref = weakref.ref(client)
    del client
    gc.collect()

    assert client_ref() is None
    assert unraisable == []
