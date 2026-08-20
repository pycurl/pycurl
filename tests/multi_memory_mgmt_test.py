import gc
import subprocess
import sys
import textwrap
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


@pytest.mark.skipif(
    sys.version_info < (3, 14),
    reason="Python 3.14 exposes callback reentrancy during tp_dealloc",
)
def test_socket_callback_not_invoked_during_multi_dealloc():
    script = textwrap.dedent(
        """
        import gc
        import pycurl

        callback_count = 0
        deallocating = False

        def socket_callback(event, fd, multi, data):
            global callback_count
            if deallocating:
                callback_count += 1

        easy = pycurl.Curl()
        easy.setopt(pycurl.URL, "http://10.255.255.1:1/")
        multi = pycurl.CurlMulti()
        multi.setopt(pycurl.M_SOCKETFUNCTION, socket_callback)
        multi.add_handle(easy)

        for _ in range(3):
            try:
                multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
            except pycurl.error:
                pass

        deallocating = True
        del multi
        gc.collect()
        print(callback_count)
        """
    )

    process = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert process.returncode == 0, process.stderr
    assert process.stdout.strip() == "0"


@pytest.mark.skipif(
    sys.version_info < (3, 14),
    reason="Python 3.14 exposes callback reentrancy during cyclic GC",
)
def test_multi_callback_cycle_is_collectable():
    script = textwrap.dedent(
        """
        import gc
        import pycurl

        class Client:
            def __init__(self):
                self.multi = pycurl.CurlMulti()
                self.multi.setopt(pycurl.M_TIMERFUNCTION, self.on_timer)
                self.multi.setopt(pycurl.M_SOCKETFUNCTION, self.on_socket)
                self.easy = pycurl.Curl()
                self.easy.setopt(pycurl.URL, "http://10.255.255.1:1/")
                self.multi.add_handle(self.easy)
                for _ in range(3):
                    try:
                        self.multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
                    except pycurl.error:
                        pass

            def on_timer(self, timeout_ms):
                pass

            def on_socket(self, event, fd, multi, data):
                pass

        for _ in range(100):
            client = Client()
            del client
            gc.collect()

        print("survived")
        """
    )

    process = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert process.returncode == 0, process.stderr
    assert process.stdout.strip() == "survived"
