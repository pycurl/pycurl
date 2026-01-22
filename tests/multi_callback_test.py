#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from urllib.parse import urlencode
from . import localhost
import logging
import pycurl
#import pytest
import select
#import sys
import time
import unittest

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(("app", 8380))


logger = logging.getLogger(__name__)


class MultiCallbackTest(unittest.TestCase):
    def setUp(self):
        self.easy = util.DefaultCurl()
        self.easy.setopt(pycurl.URL, "http://%s:8380/long_pause" % localhost)
        self.multi = pycurl.CurlMulti()
        self.multi.setopt(pycurl.M_SOCKETFUNCTION, self.socket_callback)
        self.multi.setopt(pycurl.M_TIMERFUNCTION, self.timer_callback)
        self.socket_result = None
        self.timer_result = None
        self.sockets = {}
        self.handle_added = False
        self.timer_pending = False
        self.write_calls = 0
        self.bytes_received = 0

    def tearDown(self):
        if self.handle_added:
            self.multi.remove_handle(self.easy)
        self.multi.close()
        self.easy.close()

    def socket_callback(self, ev_bitmask, sock_fd, multi, data):
        logger.debug("socket_callback: fd=%d ev=%d", sock_fd, ev_bitmask)
        self.socket_result = (sock_fd, ev_bitmask)
        if ev_bitmask & pycurl.POLL_REMOVE:
            self.sockets.pop(sock_fd)
        else:
            self.sockets[sock_fd] = ev_bitmask | self.sockets.get(sock_fd, 0)

    def timer_callback(self, timeout_ms):
        logger.debug("timer_callback: timeout=%d", timeout_ms)
        self.timer_result = timeout_ms
        if timeout_ms == 0:
            self.timer_pending = True

    def _event_loop_step(self, timeout: float = 0.2) -> None:
        self.multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)

        rset, wset, xset = self.multi.fdset()

        if not (rset or wset or xset):
            time.sleep(min(timeout, 0.01))
            return

        r_ready, w_ready, x_ready = select.select(rset, wset, xset, timeout)

        actions = {}
        for s in r_ready:
            actions[s] = actions.get(s, 0) | pycurl.CSELECT_IN
        for s in w_ready:
            actions[s] = actions.get(s, 0) | pycurl.CSELECT_OUT
        for s in x_ready:
            actions[s] = actions.get(s, 0) | pycurl.CSELECT_ERR

        for s, act in actions.items():
            self.multi.socket_action(s, act)

        if self.timer_pending:
            self.timer_pending = False
            self.multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)

    def _run_until(self, pred, timeout: float = 5.0, step_timeout: float = 0.2) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if pred():
                return True
            self._event_loop_step(
                timeout=min(step_timeout, max(0.0, deadline - time.monotonic()))
            )
        return pred()

    def partial_transfer(self, skip_first_write: bool = False):
        first_write_seen = False

        def write_callback(data):
            nonlocal first_write_seen
            logger.debug("write_callback: received %d bytes", len(data))
            first_write_seen = True
            self.write_calls += 1
            self.bytes_received += len(data)

        self.easy.setopt(pycurl.WRITEFUNCTION, write_callback)
        self.multi.add_handle(self.easy)
        self.handle_added = True
        self.multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
        assert len(self.sockets) > 0
        assert self.socket_result is not None
        assert self.timer_result is not None
        if not skip_first_write:
            ok = self._run_until(lambda: first_write_seen, timeout=10.0)
            assert ok, "Did not observe first write (or completion) in time"

    def _is_done(self) -> bool:
        _, ok_list, err_list = self.multi.info_read()
        return bool(ok_list or err_list)

    # multi.socket_action must call both SOCKETFUNCTION and TIMERFUNCTION at
    # various points during the transfer (at least at the start and end)
    def test_multi_socket_action(self):
        self.multi.add_handle(self.easy)
        self.handle_added = True
        self.multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
        assert self.socket_result is not None
        assert self.timer_result is not None

    # multi.add_handle must call TIMERFUNCTION to schedule a kick-start
    def test_multi_add_handle(self):
        self.multi.add_handle(self.easy)
        self.handle_added = True
        assert self.timer_result is not None

    # (mid-transfer) multi.remove_handle must call SOCKETFUNCTION to remove sockets
    def test_multi_remove_handle(self):
        self.multi.add_handle(self.easy)
        self.handle_added = True
        self.multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
        self.socket_result = None
        self.multi.remove_handle(self.easy)
        self.handle_added = False
        assert self.socket_result is not None

    #@pytest.mark.skipif(
    #    sys.platform == "win32", reason="https://github.com/pycurl/pycurl/issues/819"
    #)
    def test_easy_pause_unpause(self):
        params = {
            "num_chunks": 10,
            "delay": 0.2,
        }
        query = urlencode(params)
        self.easy.setopt(pycurl.URL, f"http://{localhost}:8380/chunks?{query}")
        self.partial_transfer(skip_first_write=True)

        logger.debug("Getting first write callback...")
        ok = self._run_until(lambda: self.write_calls > 0, timeout=2.0)

        assert ok, "Did not observe first write callback in time"

        assert self.write_calls > 0
        assert self.bytes_received > 0

        calls_before = self.write_calls
        bytes_before = self.bytes_received

        logger.debug("Pausing transfer...")
        self.easy.pause(pycurl.PAUSE_ALL)

        ok = self._run_until(lambda: self.write_calls > calls_before, timeout=2.0)

        assert not ok, "Transfer finished while paused"

        assert self.write_calls == calls_before
        assert self.bytes_received == bytes_before

        logger.debug("Unpausing transfer...")
        self.easy.pause(pycurl.PAUSE_CONT)

        finished = self._run_until(lambda: self._is_done(), timeout=10.0)

        assert finished, "Transfer did not finish after sleeping"
        assert self.write_calls > calls_before
        assert self.bytes_received == 70  # 10 chunks of 7 bytes each

    # (mid-transfer) easy.close() must call SOCKETFUNCTION to remove sockets
    #@pytest.mark.skipif(
    #    sys.platform in ["win32"], reason="https://github.com/pycurl/pycurl/issues/819"
    #)
    def test_easy_close(self):
        self.partial_transfer()
        self.socket_result = None
        assert self.easy.multi() == self.multi
        self.easy.close()
        assert self.easy.multi() is None
        self._run_until(lambda: self.socket_result is not None, timeout=10.0)
        assert self.socket_result is not None
