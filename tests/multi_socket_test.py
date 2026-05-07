import gc
import logging
import sys
import time
import weakref
from io import BytesIO

import flaky
import pycurl
import pytest

from . import util
from .multi_driver import install_timer_tracker, pump

logger = logging.getLogger(__name__)


@pytest.fixture
def multi():
    m = pycurl.CurlMulti()
    try:
        yield m
    finally:
        m.close()


def _find_socket(multi, timeout=5.0, timer_state=None):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
        if timer_state and timer_state.pending:
            timer_state.pending = False
            multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
        rset, wset, xset = multi.fdset()
        if rset or wset or xset:
            return (rset or wset or xset)[0]
        time.sleep(0.01)
    return None


def _assert_socket_event(event, multi, socket_events):
    for event_, multi_ in socket_events:
        if event == event_ and multi == multi_:
            return
    assert False, "%d %s not found in socket events" % (event, multi)


def _assert_within_deadline(deadline, label):
    if time.monotonic() >= deadline:
        pytest.fail(f"{label} timed out")


def _chunks_transfer(app, multi, socket_callback, label):
    """Drive a /chunks transfer on `multi` with `socket_callback` installed.

    Yields the timer_state once per drive iteration so the caller can do
    per-iteration work (e.g. assign() from outside the callback). The easy
    handle is removed and closed on exit.
    """
    timer_state = install_timer_tracker(multi)
    multi.setopt(pycurl.M_SOCKETFUNCTION, socket_callback)

    c = util.DefaultCurl()
    c.body = BytesIO()
    c.setopt(c.URL, f"{app}/chunks?num_chunks=10&delay=0.1")
    c.setopt(c.WRITEFUNCTION, c.body.write)
    multi.add_handle(c)

    try:
        running = 1
        deadline = time.monotonic() + 10.0
        while running:
            _assert_within_deadline(deadline, label)
            running = pump(multi, timer_state, timeout=0.2)
            yield timer_state
            multi.select(0.1)
    finally:
        multi.remove_handle(c)
        c.close()


def test_multi_socket(app, multi):
    urls = [
        # not sure why requesting /success produces no events.
        # see multi_socket_select_test.py for a longer explanation
        # why short wait is used there.
        f"{app}/short_wait?delay=0.10",
        f"{app}/short_wait?delay=0.11",
        f"{app}/short_wait?delay=0.12",
    ]

    socket_events = []
    timer_state = install_timer_tracker(multi)

    # socket callback
    def socket(event, socket, multi_handle, data):
        # print(event, socket, multi_handle, data)
        socket_events.append((event, multi_handle))

    # init
    multi.setopt(pycurl.M_SOCKETFUNCTION, socket)
    handles = []
    for url in urls:
        c = util.DefaultCurl()
        # save info in standard Python attributes
        c.url = url
        c.body = BytesIO()
        c.http_code = -1
        handles.append(c)
        # pycurl API calls
        c.setopt(c.URL, c.url)
        c.setopt(c.WRITEFUNCTION, c.body.write)
        multi.add_handle(c)

    # get data
    running = 1
    deadline = time.monotonic() + 10.0
    while running:
        _assert_within_deadline(deadline, "multi socket transfer")
        running = pump(multi, timer_state, timeout=0.2)
        # currently no more I/O is pending, could do something in the meantime
        # (display a progress bar, etc.)
        multi.select(0.1)

    for c in handles:
        # save info in standard Python attributes
        c.http_code = c.getinfo(c.HTTP_CODE)

    # at least in and remove events per socket
    assert len(socket_events) >= 6

    # print result
    for c in handles:
        assert "success" == c.body.getvalue().decode()
        assert 200 == c.http_code

        # multi, not curl handle
        _assert_socket_event(pycurl.POLL_IN, multi, socket_events)
        _assert_socket_event(pycurl.POLL_REMOVE, multi, socket_events)

    # close handles
    for c in handles:
        # pycurl API calls
        multi.remove_handle(c)
        c.close()


@pytest.mark.parametrize("reassign", [False, True])
def test_multi_assign_objects(app, multi, reassign):
    assigned = False
    assigned_ref = None
    first_ref = None
    seen_data = None

    class Sentinel:
        pass

    def socket(event, sock_fd, multi_handle, data):
        nonlocal seen_data
        if data is not None:
            seen_data = data

    for timer_state in _chunks_transfer(app, multi, socket, "assign objects"):
        if assigned:
            continue
        assigned_sock = _find_socket(multi, timeout=5.0, timer_state=timer_state)
        assert assigned_sock is not None
        first = Sentinel()
        first_ref = weakref.ref(first)
        rc_before = sys.getrefcount(first)
        multi.assign(assigned_sock, first)
        rc_after = sys.getrefcount(first)
        assert rc_after >= rc_before + 1
        if reassign:
            second = Sentinel()
            rc2_before = sys.getrefcount(second)
            assigned_ref = weakref.ref(second)
            multi.assign(assigned_sock, second)
            rc2_after = sys.getrefcount(second)
            assert rc2_after >= rc2_before + 1
            del second
        else:
            assigned_ref = first_ref
        assigned = True
        del first

    assert assigned_ref is not None
    assert first_ref is not None
    gc.collect()
    if reassign:
        assert first_ref() is None
    else:
        assert first_ref() is assigned_ref()
    assert assigned_ref() is not None
    assert seen_data is assigned_ref()
    seen_data = None
    multi.close()
    gc.collect()
    assert first_ref() is None
    assert assigned_ref() is None


def test_multi_assign_inside_socket_callback(app, multi):
    class Marker:
        pass

    marker = Marker()
    events = []
    assign_errors = []

    def socket(event, sock_fd, multi_handle, data):
        events.append((sock_fd, event, data))
        if event != pycurl.POLL_REMOVE and data is None:
            try:
                multi.assign(sock_fd, marker)
            except pycurl.error as e:
                assign_errors.append(e)

    for _ in _chunks_transfer(app, multi, socket, "assign in callback"):
        pass

    assert assign_errors == []
    assert any(data is marker for _, _, data in events), (
        "expected at least one callback to receive the assigned marker as socketp"
    )


def test_socketp_starts_as_none(app, multi):
    seen_per_fd: dict[int, list] = {}

    def socket(event, sock_fd, multi_handle, data):
        seen_per_fd.setdefault(sock_fd, []).append(data)

    for _ in _chunks_transfer(app, multi, socket, "socketp starts None"):
        pass

    assert seen_per_fd, "expected at least one socket callback invocation"
    for fd, datas in seen_per_fd.items():
        assert all(d is None for d in datas), (
            f"fd={fd} received non-None socketp without assign(): {datas!r}"
        )


@flaky.flaky(max_runs=3)
@pytest.mark.parametrize(
    "clear",
    [
        lambda multi, sock: multi.unassign(sock),
        lambda multi, sock: multi.assign(sock, None),
    ],
    ids=["unassign", "assign_none"],
)
def test_clear_assignment_inside_socket_callback_releases_ref(app, multi, clear):
    class Marker:
        pass

    marker = Marker()
    # why: weakref keeps the closure from pinning marker and defeating the GC check below.
    marker_ref = weakref.ref(marker)
    errors = []
    cleared_fds = set()

    def socket(event, sock_fd, multi_handle, data):
        # why: log primitives only -- passing `data` would pin marker via LogRecord args.
        kind = (
            "None" if data is None else ("marker" if data is marker_ref() else "other")
        )
        logger.debug(
            "socket_cb event=%d fd=%d data=%s cleared_fds=%s",
            event,
            sock_fd,
            kind,
            sorted(cleared_fds),
        )
        try:
            if data is marker_ref():
                clear(multi, sock_fd)
                cleared_fds.add(sock_fd)
            elif data is None and not cleared_fds and event != pycurl.POLL_REMOVE:
                multi.assign(sock_fd, marker_ref())
        except pycurl.error as e:
            errors.append(e)

    for _ in _chunks_transfer(app, multi, socket, "clear in callback"):
        pass

    assert errors == [], errors
    assert cleared_fds, "did not reach clear inside callback"
    del marker
    gc.collect()
    assert marker_ref() is None, (
        "expected multi to drop strong ref to marker after clear"
    )


def _assign_marker_then_close(app):
    multi = pycurl.CurlMulti()
    timer_state = install_timer_tracker(multi)

    class Marker:
        pass

    marker = Marker()
    marker_ref = weakref.ref(marker)
    state = {"assigned": False}

    def socket(event, sock_fd, multi_handle, data):
        if event != pycurl.POLL_REMOVE and not state["assigned"]:
            multi.assign(sock_fd, marker)
            state["assigned"] = True

    multi.setopt(pycurl.M_SOCKETFUNCTION, socket)

    c = util.DefaultCurl()
    c.body = BytesIO()
    c.setopt(c.URL, f"{app}/chunks?num_chunks=20&delay=0.05")
    c.setopt(c.WRITEFUNCTION, c.body.write)
    multi.add_handle(c)

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and not state["assigned"]:
        pump(multi, timer_state, timeout=0.1)

    assert state["assigned"], "did not assign marker before timeout"

    multi.remove_handle(c)
    c.close()
    multi.close()
    return marker_ref


def test_close_releases_assigned_marker(app):
    marker_ref = _assign_marker_then_close(app)
    gc.collect()
    assert marker_ref() is None, "marker still alive after close()"


@pytest.mark.parametrize(
    "clear",
    [
        lambda multi, sock: multi.assign(sock, None),
        lambda multi, sock: multi.unassign(sock),
    ],
    ids=["assign_none", "unassign"],
)
def test_multi_clear_assignment(app, multi, clear):
    """assign(fd, None) and unassign(fd) both clear the association and
    release the strong reference to the previously assigned object."""
    assigned_sock = None
    assigned_ref = None

    class Sentinel:
        pass

    def socket(event, sock_fd, multi_handle, data):
        pass

    for timer_state in _chunks_transfer(app, multi, socket, "clear assignment"):
        if assigned_sock is not None:
            continue
        assigned_sock = _find_socket(multi, timeout=5.0, timer_state=timer_state)
        assert assigned_sock is not None
        sentinel = Sentinel()
        assigned_ref = weakref.ref(sentinel)
        rc_before = sys.getrefcount(sentinel)
        multi.assign(assigned_sock, sentinel)
        rc_after = sys.getrefcount(sentinel)
        assert rc_after >= rc_before + 1
        clear(multi, assigned_sock)
        del sentinel

    assert assigned_ref is not None
    gc.collect()
    assert assigned_ref() is None
