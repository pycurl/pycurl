#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Generator
from urllib.parse import urlencode
import logging
import pycurl
import pytest
import select
import time
from . import util

logger = logging.getLogger(__name__)


@dataclass
class MultiCtx:
    easy: pycurl.Curl
    multi: pycurl.CurlMulti

    socket_result: tuple[int, int] | None = None
    timer_result: int | None = None
    sockets: dict[int, int] = field(default_factory=dict)

    handle_added: bool = False
    timer_pending: bool = False

    write_calls: int = 0
    bytes_received: int = 0


def _event_loop_step(ctx: MultiCtx, timeout: float = 0.2) -> None:
    ctx.multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)

    rset, wset, xset = ctx.multi.fdset()

    if not (rset or wset or xset):
        time.sleep(min(timeout, 0.01))
        return

    r_ready, w_ready, x_ready = select.select(rset, wset, xset, timeout)

    actions: dict[int, int] = {}
    for s in r_ready:
        actions[s] = actions.get(s, 0) | pycurl.CSELECT_IN
    for s in w_ready:
        actions[s] = actions.get(s, 0) | pycurl.CSELECT_OUT
    for s in x_ready:
        actions[s] = actions.get(s, 0) | pycurl.CSELECT_ERR

    for s, act in actions.items():
        ctx.multi.socket_action(s, act)

    if ctx.timer_pending:
        ctx.timer_pending = False
        ctx.multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)


def _run_until(
    ctx: MultiCtx,
    pred: Callable[[], bool],
    timeout: float = 5.0,
    step_timeout: float = 0.2,
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        _event_loop_step(
            ctx,
            timeout=min(step_timeout, max(0.0, deadline - time.monotonic())),
        )
    return pred()


def _is_done(ctx: MultiCtx) -> bool:
    _, ok_list, err_list = ctx.multi.info_read()
    return bool(ok_list or err_list)


def partial_transfer(ctx: MultiCtx, skip_first_write: bool = False) -> None:
    first_write_seen = False

    def write_callback(data: bytes) -> None:
        nonlocal first_write_seen
        logger.debug("write_callback: received %d bytes", len(data))
        first_write_seen = True
        ctx.write_calls += 1
        ctx.bytes_received += len(data)

    ctx.easy.setopt(pycurl.WRITEFUNCTION, write_callback)
    ctx.multi.add_handle(ctx.easy)
    ctx.handle_added = True

    ctx.multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)

    ok = _run_until(ctx, lambda: len(ctx.sockets) > 0, timeout=5.0)
    assert ok, "Did not observe socket registration in time"
    assert ctx.socket_result is not None
    assert ctx.timer_result is not None

    if not skip_first_write:
        ok = _run_until(ctx, lambda: first_write_seen, timeout=10.0)
        assert ok, "Did not observe first write (or completion) in time"


@pytest.fixture
def multi_ctx(app) -> Generator[MultiCtx, None, None]:
    easy = util.DefaultCurl()
    easy.setopt(pycurl.URL, f"{app}/long_pause")

    multi = pycurl.CurlMulti()
    ctx = MultiCtx(easy=easy, multi=multi)

    def socket_callback(ev_bitmask: int, sock_fd: int, multi_handle, data) -> None:
        logger.debug("socket_callback: fd=%d ev=%d", sock_fd, ev_bitmask)
        ctx.socket_result = (sock_fd, ev_bitmask)
        if ev_bitmask & pycurl.POLL_REMOVE:
            ctx.sockets.pop(sock_fd, None)
        else:
            ctx.sockets[sock_fd] = ev_bitmask | ctx.sockets.get(sock_fd, 0)

    def timer_callback(timeout_ms: int) -> None:
        logger.debug("timer_callback: timeout=%d", timeout_ms)
        ctx.timer_result = timeout_ms
        if timeout_ms == 0:
            ctx.timer_pending = True

    multi.setopt(pycurl.M_SOCKETFUNCTION, socket_callback)
    multi.setopt(pycurl.M_TIMERFUNCTION, timer_callback)

    try:
        yield ctx
    finally:
        if ctx.handle_added:
            try:
                ctx.multi.remove_handle(ctx.easy)
            except Exception:
                # best-effort cleanup
                pass
        ctx.multi.close()
        ctx.easy.close()


# multi.socket_action must call both SOCKETFUNCTION and TIMERFUNCTION at
# various points during the transfer (at least at the start and end)
def test_multi_socket_action(multi_ctx: MultiCtx):
    multi_ctx.multi.add_handle(multi_ctx.easy)
    multi_ctx.handle_added = True

    multi_ctx.multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)

    assert multi_ctx.socket_result is not None
    assert multi_ctx.timer_result is not None


# multi.add_handle must call TIMERFUNCTION to schedule a kick-start
def test_multi_add_handle(multi_ctx: MultiCtx):
    multi_ctx.multi.add_handle(multi_ctx.easy)
    multi_ctx.handle_added = True
    assert multi_ctx.timer_result is not None


# (mid-transfer) multi.remove_handle must call SOCKETFUNCTION to remove sockets
def test_multi_remove_handle(multi_ctx: MultiCtx):
    multi_ctx.multi.add_handle(multi_ctx.easy)
    multi_ctx.handle_added = True

    multi_ctx.multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)

    multi_ctx.socket_result = None
    multi_ctx.multi.remove_handle(multi_ctx.easy)
    multi_ctx.handle_added = False

    assert multi_ctx.socket_result is not None


def test_easy_pause_unpause(multi_ctx: MultiCtx, app):
    params = {"num_chunks": 10, "delay": 0.2}
    query = urlencode(params)
    multi_ctx.easy.setopt(pycurl.URL, f"{app}/chunks?{query}")

    partial_transfer(multi_ctx, skip_first_write=True)

    logger.debug("Getting first write callback...")
    ok = _run_until(multi_ctx, lambda: multi_ctx.write_calls > 0, timeout=2.0)
    assert ok, "Did not observe first write callback in time"
    assert multi_ctx.write_calls > 0
    assert multi_ctx.bytes_received > 0

    calls_before = multi_ctx.write_calls
    bytes_before = multi_ctx.bytes_received

    logger.debug("Pausing transfer...")
    multi_ctx.easy.pause(pycurl.PAUSE_ALL)

    ok = _run_until(
        multi_ctx, lambda: multi_ctx.write_calls > calls_before, timeout=2.0
    )
    assert not ok, "Transfer finished while paused"
    assert multi_ctx.write_calls == calls_before
    assert multi_ctx.bytes_received == bytes_before

    logger.debug("Unpausing transfer...")
    multi_ctx.easy.unpause()

    finished = _run_until(multi_ctx, lambda: _is_done(multi_ctx), timeout=10.0)
    assert finished, "Transfer did not finish after sleeping"
    assert multi_ctx.write_calls > calls_before
    assert multi_ctx.bytes_received == 70  # 10 chunks of 7 bytes each


# (mid-transfer) easy.close() must call SOCKETFUNCTION to remove sockets
def test_easy_close(multi_ctx: MultiCtx):
    partial_transfer(multi_ctx)

    multi_ctx.socket_result = None
    assert multi_ctx.easy.multi() == multi_ctx.multi

    multi_ctx.easy.close()
    assert multi_ctx.easy.multi() is None

    _run_until(multi_ctx, lambda: multi_ctx.socket_result is not None, timeout=10.0)
    assert multi_ctx.socket_result is not None
