import gc
import sys
import weakref

import pycurl
import pytest

from . import util


_MULTI_CALLBACKS = [
    pytest.param(pycurl.M_SOCKETFUNCTION, id="M_SOCKETFUNCTION"),
    pytest.param(pycurl.M_TIMERFUNCTION, id="M_TIMERFUNCTION"),
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
