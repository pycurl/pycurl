#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import gc
import select
import sys
import time
import weakref

import pycurl
import pytest

from . import util


@pytest.fixture
def multi():
    m = pycurl.CurlMulti()
    try:
        yield m
    finally:
        m.close()


def _setup_timer(multi):
    timer_state = {"pending": False}

    def timer(timeout_ms):
        if timeout_ms == 0:
            timer_state["pending"] = True

    multi.setopt(pycurl.M_TIMERFUNCTION, timer)
    return timer_state


def _consume_timer(multi, timer_state):
    if timer_state and timer_state["pending"]:
        timer_state["pending"] = False
        multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)


def _drive_multi(multi, timeout=0.2, timer_state=None):
    _, running = multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)

    rset, wset, xset = multi.fdset()
    if not (rset or wset or xset):
        _consume_timer(multi, timer_state)
        time.sleep(min(timeout, 0.01))
        return running

    r_ready, w_ready, x_ready = select.select(rset, wset, xset, timeout)
    actions = {}
    for s in r_ready:
        actions[s] = actions.get(s, 0) | pycurl.CSELECT_IN
    for s in w_ready:
        actions[s] = actions.get(s, 0) | pycurl.CSELECT_OUT
    for s in x_ready:
        actions[s] = actions.get(s, 0) | pycurl.CSELECT_ERR

    for s, act in actions.items():
        _, running = multi.socket_action(s, act)

    _consume_timer(multi, timer_state)
    return running


def _find_socket(multi, timeout=5.0, timer_state=None):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
        _consume_timer(multi, timer_state)
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
    timer_state = _setup_timer(multi)

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
        c.body = util.BytesIO()
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
        running = _drive_multi(multi, timeout=0.2, timer_state=timer_state)
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
@pytest.mark.skipif(sys.platform == "win32", reason="flaky on win32")
def test_multi_assign_objects(app, multi, reassign):
    url = f"{app}/chunks?num_chunks=10&delay=0.1"

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

    timer_state = _setup_timer(multi)
    multi.setopt(pycurl.M_SOCKETFUNCTION, socket)
    c = util.DefaultCurl()
    c.body = util.BytesIO()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEFUNCTION, c.body.write)
    multi.add_handle(c)

    running = 1
    deadline = time.monotonic() + 10.0
    while running:
        _assert_within_deadline(deadline, "multi assign objects transfer")
        running = _drive_multi(multi, timeout=0.2, timer_state=timer_state)
        if not assigned:
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
        multi.select(0.1)

    multi.remove_handle(c)
    c.close()

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


@pytest.mark.skipif(sys.platform == "win32", reason="flaky on win32")
def test_multi_assign_none_clears(app, multi):
    url = f"{app}/chunks?num_chunks=10&delay=0.1"

    assigned_sock = None
    assigned_ref = None

    class Sentinel:
        pass

    def socket(event, sock_fd, multi_handle, data):
        pass

    timer_state = _setup_timer(multi)
    multi.setopt(pycurl.M_SOCKETFUNCTION, socket)
    c = util.DefaultCurl()
    c.body = util.BytesIO()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEFUNCTION, c.body.write)
    multi.add_handle(c)

    running = 1
    deadline = time.monotonic() + 10.0
    while running:
        _assert_within_deadline(deadline, "multi assign none clears transfer")
        running = _drive_multi(multi, timeout=0.2, timer_state=timer_state)
        if assigned_sock is None:
            assigned_sock = _find_socket(multi, timeout=5.0, timer_state=timer_state)
            assert assigned_sock is not None
            sentinel = Sentinel()
            assigned_ref = weakref.ref(sentinel)
            rc_before = sys.getrefcount(sentinel)
            multi.assign(assigned_sock, sentinel)
            rc_after = sys.getrefcount(sentinel)
            assert rc_after >= rc_before + 1
            multi.assign(assigned_sock, None)
            del sentinel
        multi.select(0.1)

    multi.remove_handle(c)
    c.close()

    assert assigned_ref is not None
    gc.collect()
    assert assigned_ref() is None
