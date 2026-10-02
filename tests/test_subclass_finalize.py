import datetime
import gc
import socket
import sys
import threading
import time
import types
import weakref

import pytest

import pycurl

from . import util


def raise_value_error(*args):
    raise ValueError("boom")


def raising_closesocketfunction(fds):
    def closesocketfunction(curlfd):
        fds.append(curlfd)
        raise ValueError("boom")

    return closesocketfunction


def recording_closesocketfunction(calls):
    def closesocketfunction(curlfd):
        calls.append(curlfd)
        socket.socket(fileno=curlfd).close()
        return 0

    return closesocketfunction


def preload_hsts(curl, hstswrite):
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    entries = [(b"example.com", expire, True)]
    curl.setopt(pycurl.HSTS_CTRL, pycurl.CURLHSTS_ENABLE)
    curl.setopt(pycurl.HSTSREADFUNCTION, lambda: entries.pop() if entries else None)
    curl.setopt(pycurl.HSTSWRITEFUNCTION, hstswrite)


def connect(curl, listener):
    curl.setopt(pycurl.URL, f"http://127.0.0.1:{listener.port}/")
    curl.setopt(pycurl.CONNECT_ONLY, True)
    curl.perform()
    return listener.accept()


def base():
    return pycurl.Curl()


def plain_subclass():
    class MyCurl(pycurl.Curl):
        pass

    return MyCurl()


def del_override():
    class MyCurl(pycurl.Curl):
        def __del__(self):
            pass

    return MyCurl()


def del_override_in_cycle():
    curl = del_override()
    curl.myself = curl
    return curl


@pytest.mark.parametrize(
    "make_curl", [base, plain_subclass, del_override, del_override_in_cycle]
)
def test_handle_closes_its_socket(listener, make_curl):
    curl = make_curl()
    conn = connect(curl, listener)

    del curl
    gc.collect()
    assert listener.peer_closed(conn)


def test_del_storing_self_keeps_handle_open(listener):
    saved = []

    class MyCurl(pycurl.Curl):
        def __del__(self):
            saved.append(self)

    curl = MyCurl()
    conn = connect(curl, listener)

    del curl
    gc.collect()
    assert not listener.peer_closed(conn)
    assert len(saved) == 1
    assert saved[0].closed is False
    assert saved[0].getinfo(pycurl.ACTIVESOCKET) != -1
    saved[0].close()


def test_multi_subclass_del_releases_easy():
    class MyMulti(pycurl.CurlMulti):
        def __del__(self):
            pass

    multi = MyMulti()
    curl = pycurl.Curl()
    multi.add_handle(curl)
    ref = weakref.ref(curl)

    del curl
    gc.collect()
    assert ref() is not None, "the multi should keep the easy alive"

    del multi
    gc.collect()
    assert ref() is None


def test_closesocketfunction_raising_during_dealloc(listener, unraisable):
    fds = []
    curl = pycurl.Curl()
    curl.setopt(pycurl.CLOSESOCKETFUNCTION, raising_closesocketfunction(fds))
    connect(curl, listener)

    del curl
    gc.collect()
    assert unraisable == [ValueError]
    # Fails if pycurl closed it behind the callback.
    socket.socket(fileno=fds[0]).close()


def test_closesocketfunction_raising_during_close(listener, unraisable):
    fds = []
    curl = pycurl.Curl()
    curl.setopt(pycurl.CLOSESOCKETFUNCTION, raising_closesocketfunction(fds))
    connect(curl, listener)

    assert curl.close() is None
    assert curl.closed
    assert unraisable == [ValueError]
    socket.socket(fileno=fds[0]).close()


def test_pending_exception_does_not_skip_closesocketfunction(listener):
    calls = []
    conns = []
    closesocketfunction = recording_closesocketfunction(calls)

    def connected():
        curl = pycurl.Curl()
        curl.setopt(pycurl.CLOSESOCKETFUNCTION, closesocketfunction)
        conns.append(connect(curl, listener))
        return curl

    # The handle dies while the TypeError from sorted() is still propagating.
    with pytest.raises(TypeError):
        sorted([connected(), "a"])
    gc.collect()

    assert calls, "the callback must run even with an exception pending"
    assert listener.peer_closed(conns[0])


@pytest.mark.parametrize("exc_type", [ValueError, KeyboardInterrupt])
@pytest.mark.parametrize("teardown", ["dealloc", "close"])
def test_multi_timer_error_during_teardown(unraisable, exc_type, teardown):
    tearing_down = []

    def timerfunction(timeout_ms):
        if tearing_down:
            raise exc_type("timer boom")
        return 0

    multi = pycurl.CurlMulti()
    multi.setopt(pycurl.M_TIMERFUNCTION, timerfunction)
    curl = pycurl.Curl()
    multi.add_handle(curl)

    del curl
    tearing_down.append(True)
    if teardown == "close":
        try:
            closed = multi.close()
        except exc_type as exc:
            pytest.fail(f"close() must not propagate {exc!r}")
        assert closed is None
    else:
        del multi
    gc.collect()
    assert set(unraisable) == {exc_type}


@util.min_libcurl(7, 32, 0)
def test_progress_error_during_multi_teardown(listener, unraisable):
    calls = []
    tearing_down = []

    def xferinfofunction(*args):
        if tearing_down:
            raise ValueError("progress boom")
        calls.append(args)
        return 0

    multi = pycurl.CurlMulti()
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, f"http://127.0.0.1:{listener.port}/")
    curl.setopt(pycurl.NOPROGRESS, False)
    curl.setopt(pycurl.XFERINFOFUNCTION, xferinfofunction)
    multi.add_handle(curl)
    deadline = time.monotonic() + 10.0
    running = True
    while running and not calls and time.monotonic() < deadline:
        _, running = multi.perform()
        multi.select(0.1)
    assert calls, "the transfer never reported progress"

    tearing_down.append(True)
    del curl, multi
    gc.collect()
    assert set(unraisable) == {ValueError}


@util.min_libcurl(7, 74, 0)
def test_hstswrite_raising_during_dealloc(listener, unraisable):
    curl = pycurl.Curl()
    preload_hsts(curl, raise_value_error)
    conn = connect(curl, listener)

    del curl
    gc.collect()
    assert unraisable == [ValueError]
    assert listener.peer_closed(conn)


@util.min_libcurl(7, 74, 0)
def test_del_without_super_skips_hstswrite(listener):
    written = []

    class MyCurl(pycurl.Curl):
        def __del__(self):
            pass

    curl = MyCurl()
    preload_hsts(curl, lambda entry, index: written.append(entry))
    conn = connect(curl, listener)

    del curl
    gc.collect()
    assert written == []
    assert listener.peer_closed(conn)


def test_del_without_super_skips_callback_but_closes_socket(listener):
    calls = []

    class MyCurl(pycurl.Curl):
        def __del__(self):
            pass

    curl = MyCurl()
    curl.setopt(pycurl.CLOSESOCKETFUNCTION, lambda curlfd: calls.append(curlfd))
    conn = connect(curl, listener)

    del curl
    gc.collect()
    assert calls == []
    assert listener.peer_closed(conn)


def test_del_with_super_invokes_callback(listener):
    calls = []

    class MyCurl(pycurl.Curl):
        def __del__(self):
            super().__del__()

    curl = MyCurl()
    curl.setopt(pycurl.CLOSESOCKETFUNCTION, recording_closesocketfunction(calls))
    conn = connect(curl, listener)

    del curl
    gc.collect()
    assert calls
    assert listener.peer_closed(conn)


def test_explicit_del_is_idempotent(listener, unraisable):
    curl = pycurl.Curl()
    conn = connect(curl, listener)

    curl.__del__()
    assert curl.closed
    assert listener.peer_closed(conn)
    curl.__del__()

    del curl
    gc.collect()
    assert unraisable == []


def test_explicit_del_while_running_is_refused(listener, unraisable):
    curl = pycurl.Curl()

    def sockoptfunction(curlfd, purpose):
        curl.__del__()
        return 0

    curl.setopt(pycurl.SOCKOPTFUNCTION, sockoptfunction)
    conn = connect(curl, listener)

    assert unraisable == [pycurl.error]
    assert not curl.closed
    curl.close()
    assert listener.peer_closed(conn)


def test_nested_del_keeps_the_teardown_window_open(listener, unraisable):
    curl = pycurl.Curl()

    def closesocketfunction(curlfd):
        curl.__del__()
        socket.socket(fileno=curlfd).close()
        raise ValueError("boom")

    curl.setopt(pycurl.CLOSESOCKETFUNCTION, closesocketfunction)
    connect(curl, listener)

    assert curl.close() is None
    assert unraisable == [pycurl.error, ValueError]


@pytest.mark.skipif(
    sys.version_info[:2] == (3, 13),
    reason="3.13 defers to the trashcan by a C recursion counter, not by stack use",
)
def test_long_chain_of_handles_does_not_exhaust_the_stack():
    freed = []

    def build_and_drop():
        head = pycurl.Curl()
        curl = head
        for _ in range(10000):
            following = pycurl.Curl()
            curl.setopt(
                pycurl.WRITEFUNCTION, types.MethodType(lambda *args: None, following)
            )
            curl = following
        tail = weakref.ref(curl)

        del curl, following, head
        freed.append(tail() is None)

    previous = threading.stack_size(512 * 1024)
    try:
        thread = threading.Thread(target=build_and_drop)
        thread.start()
        thread.join()
    finally:
        threading.stack_size(previous)
    assert freed == [True]


def test_dealloc_preserves_a_propagating_exception(listener, unraisable):
    fds = []
    closesocketfunction = raising_closesocketfunction(fds)

    def connected():
        curl = pycurl.Curl()
        curl.setopt(pycurl.CLOSESOCKETFUNCTION, closesocketfunction)
        connect(curl, listener)
        return curl

    with pytest.raises(TypeError):
        sorted([connected(), "a"])
    gc.collect()

    assert unraisable == [ValueError]
    socket.socket(fileno=fds[0]).close()
