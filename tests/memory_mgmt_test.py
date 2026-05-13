import gc
import sys
import weakref

import pycurl
import pytest

from . import util
from .util import LiveTracker, gc_collect_hard


devnull = "NUL" if sys.platform == "win32" else "/dev/null"


def _populate_multi(multi, count):
    tr = LiveTracker()
    tr.track("multi", multi)
    handles = []
    for i in range(count):
        c = util.DefaultCurl()
        tr.track(f"easy[{i}]", c)
        multi.add_handle(c)
        handles.append(c)
    return tr, handles


def _populate_share(share, count):
    tr = LiveTracker()
    tr.track("share", share)
    handles = []
    for i in range(count):
        c = util.DefaultCurl()
        tr.track(f"easy[{i}]", c)
        c.setopt(c.SHARE, share)
        handles.append(c)
    return tr, handles


def test_multi_releases_easies_after_close_and_remove():
    multi = pycurl.CurlMulti()
    tr, handles = _populate_multi(multi, 100)

    for c in handles:
        c.close()
        multi.remove_handle(c)

    del c, handles, multi
    tr.assert_all_gone()


def test_multi_cycle_collected_by_gc():
    multi = pycurl.CurlMulti()
    tr, handles = _populate_multi(multi, 100)

    del handles, multi
    tr.assert_all_gone()


def test_share_releases_easies_after_unsetopt_and_close():
    share = pycurl.CurlShare()
    tr, handles = _populate_share(share, 100)

    for c in handles:
        c.unsetopt(c.SHARE)
        c.close()

    del c, handles, share
    tr.assert_all_gone()


def test_share_cycle_collected_by_gc():
    share = pycurl.CurlShare()
    tr, handles = _populate_share(share, 100)

    del handles, share
    tr.assert_all_gone()


def test_reference_counting():
    c = util.DefaultCurl()
    m = pycurl.CurlMulti()
    m.add_handle(c)
    del m
    m = pycurl.CurlMulti()
    c.close()
    del m, c


def test_self_referential_curl_collected_via_gc():
    c = util.DefaultCurl()
    c.m = pycurl.CurlMulti()
    c.m.add_handle(c)
    c.c = c
    c.c.c1 = c
    c.c.c2 = c
    c.c.c3 = c.c
    c.c.c4 = c.m
    c.m.c = c
    c.m.m = c.m

    ref = weakref.ref(c)
    del c
    gc_collect_hard()
    assert ref() is None


def test_refcounting_bug_in_reset():
    iters = 10000 if sys.platform == "win32" else 100000
    for _ in range(iters):
        c = util.DefaultCurl()
        c.reset()
        c.close()


def test_postfields_unicode_memory_leak_gh252():
    c = util.DefaultCurl()
    gc.collect()
    before = len(gc.get_objects())

    for _ in range(100000):
        c.setopt(pycurl.POSTFIELDS, util.u("hello world"))

    gc.collect()
    after = len(gc.get_objects())
    assert after <= before + 1000, f"object count grew {before} -> {after}"
    c.close()


def test_form_bufferptr_memory_leak_gh267():
    c = util.DefaultCurl()
    gc.collect()
    before = len(gc.get_objects())

    for _ in range(100000):
        with pytest.warns(
            DeprecationWarning, match="HTTPPOST is deprecated; use MIMEPOST"
        ):
            # libcurl 7.19.0 requires FORM_BUFFER before FORM_BUFFERPTR;
            # newer versions accept FORM_BUFFERPTR alone and reproduce the leak.
            c.setopt(
                pycurl.HTTPPOST,
                [
                    (
                        "post1",
                        (pycurl.FORM_BUFFER, "foo.txt", pycurl.FORM_BUFFERPTR, "data1"),
                    ),
                    (
                        "post2",
                        (pycurl.FORM_BUFFER, "bar.txt", pycurl.FORM_BUFFERPTR, "data2"),
                    ),
                ],
            )

    gc.collect()
    after = len(gc.get_objects())
    assert after <= before + 1000, f"object count grew {before} -> {after}"
    c.close()


@pytest.mark.parametrize(
    "option,target",
    [
        pytest.param(pycurl.READDATA, lambda f: f, id="READDATA"),
        pytest.param(pycurl.WRITEDATA, lambda f: f, id="WRITEDATA"),
        pytest.param(pycurl.WRITEHEADER, lambda f: f, id="WRITEHEADER"),
        pytest.param(pycurl.READFUNCTION, lambda f: f.read, id="READFUNCTION"),
        pytest.param(pycurl.WRITEFUNCTION, lambda f: f.write, id="WRITEFUNCTION"),
        pytest.param(pycurl.HEADERFUNCTION, lambda f: f.write, id="HEADERFUNCTION"),
    ],
)
def test_option_refcounting(option, target):
    c = util.DefaultCurl()
    f = open(devnull, "a+")
    obj = target(f)
    c.setopt(option, obj)
    ref = weakref.ref(obj)
    del f, obj
    gc.collect()
    assert ref() is not None

    for _ in range(100):
        assert ref() is not None
        c.setopt(option, ref())
    gc.collect()
    assert ref() is not None

    c.close()
    gc.collect()
    assert ref() is None


_CALLBACK_RELEASE_PARAMS = [
    pytest.param(pycurl.WRITEFUNCTION, None, id="WRITEFUNCTION"),
    pytest.param(pycurl.HEADERFUNCTION, None, id="HEADERFUNCTION"),
    pytest.param(pycurl.READFUNCTION, None, id="READFUNCTION"),
    pytest.param(
        pycurl.PROGRESSFUNCTION,
        "PROGRESSFUNCTION is deprecated; use XFERINFOFUNCTION",
        id="PROGRESSFUNCTION",
    ),
    pytest.param(
        pycurl.XFERINFOFUNCTION,
        None,
        id="XFERINFOFUNCTION",
        marks=pytest.mark.skipif(
            util.pycurl_version_less_than(7, 32, 0),
            reason="libcurl < 7.32.0",
        ),
    ),
    pytest.param(pycurl.DEBUGFUNCTION, None, id="DEBUGFUNCTION"),
    pytest.param(
        pycurl.IOCTLFUNCTION,
        "IOCTLFUNCTION is deprecated; use SEEKFUNCTION",
        id="IOCTLFUNCTION",
    ),
    pytest.param(pycurl.OPENSOCKETFUNCTION, None, id="OPENSOCKETFUNCTION"),
    pytest.param(pycurl.SEEKFUNCTION, None, id="SEEKFUNCTION"),
]


@pytest.mark.parametrize("callback,deprecation_match", _CALLBACK_RELEASE_PARAMS)
def test_callback_released_on_close(callback, deprecation_match):
    def cb(x):
        return True

    ref = weakref.ref(cb)

    c = util.DefaultCurl()
    if deprecation_match:
        with pytest.warns(DeprecationWarning, match=deprecation_match):
            c.setopt(callback, cb)
    else:
        c.setopt(callback, cb)
    del cb
    assert ref() is not None, "C extension should still hold the callback"

    del c
    gc.collect()
    assert ref() is None, "callback should be released after handle is destroyed"
