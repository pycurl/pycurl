"""Helpers for driving curl_multi_socket_action in tests."""

from __future__ import annotations

import select
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pycurl


@dataclass
class TimerState:
    pending: bool = False


def install_timer_tracker(
    multi: pycurl.CurlMulti,
    base_cb: Callable[[int], Any] | None = None,
) -> TimerState:
    """Install M_TIMERFUNCTION; record timeout_ms == 0 in a TimerState.

    `base_cb`, if provided, is called and its return value forwarded to
    libcurl, so callers can install an arbitrary user callback without
    losing the pending-timer signal.
    """
    state = TimerState()

    def timer(timeout_ms: int) -> Any:
        if timeout_ms == 0:
            state.pending = True
        return None if base_cb is None else base_cb(timeout_ms)

    multi.setopt(pycurl.M_TIMERFUNCTION, timer)
    return state


def pump(multi: pycurl.CurlMulti, timer_state: TimerState, timeout: float = 0.2) -> int:
    """Run one event-loop tick; return the number of running handles."""
    _, running = multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
    rset, wset, xset = multi.fdset()
    if not (rset or wset or xset):
        if timer_state.pending:
            timer_state.pending = False
            _, running = multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
        time.sleep(min(timeout, 0.01))
        return running

    r, w, x = select.select(rset, wset, xset, timeout)
    actions = {}
    for s in r:
        actions[s] = actions.get(s, 0) | pycurl.CSELECT_IN
    for s in w:
        actions[s] = actions.get(s, 0) | pycurl.CSELECT_OUT
    for s in x:
        actions[s] = actions.get(s, 0) | pycurl.CSELECT_ERR
    for s, act in actions.items():
        _, running = multi.socket_action(s, act)

    if timer_state.pending:
        timer_state.pending = False
        _, running = multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
    return running
