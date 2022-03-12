#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import pycurl
import pytest
import sys
import unittest

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class MultiCallbackTest(unittest.TestCase):
    def setUp(self):
        self.easy = util.DefaultCurl()
        self.easy.setopt(pycurl.URL, 'http://%s:8380/long_pause' % localhost)
        self.multi = pycurl.CurlMulti()
        self.multi.setopt(pycurl.M_SOCKETFUNCTION, self.socket_callback)
        self.multi.setopt(pycurl.M_TIMERFUNCTION, self.timer_callback)
        self.socket_result = None
        self.timer_result = None
        self.sockets = {}

    def tearDown(self):
        self.multi.close()
        self.easy.close()

    def socket_callback(self, ev_bitmask, sock_fd, multi, data):
        self.socket_result = (sock_fd, ev_bitmask)
        if ev_bitmask & pycurl.POLL_REMOVE:
            self.sockets.pop(sock_fd)
        else:
            self.sockets[sock_fd] = ev_bitmask | self.sockets.get(sock_fd, 0)

    def timer_callback(self, timeout_ms):
        self.timer_result = timeout_ms

    def partial_transfer(self):
        perform = True
        def write_callback(data):
            nonlocal perform
            perform = False
        self.easy.setopt(pycurl.WRITEFUNCTION, write_callback)
        self.multi.add_handle(self.easy)
        self.multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
        while self.sockets and perform:
            for socket, action in tuple(self.sockets.items()):
                self.multi.socket_action(socket, action)

    # multi.socket_action must call both SOCKETFUNCTION and TIMERFUNCTION at
    # various points during the transfer (at least at the start and end)
    @pytest.mark.xfail(sys.platform == 'darwin', reason='https://github.com/pycurl/pycurl/issues/729')
    def test_multi_socket_action(self):
        self.multi.add_handle(self.easy)
        self.timer_result = None
        self.socket_result = None
        self.multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
        assert self.socket_result is not None
        assert self.timer_result is not None

    # multi.add_handle must call TIMERFUNCTION to schedule a kick-start
    def test_multi_add_handle(self):
        self.multi.add_handle(self.easy)
        assert self.timer_result is not None

    # (mid-transfer) multi.remove_handle must call SOCKETFUNCTION to remove sockets
    @pytest.mark.xfail(sys.platform == 'darwin', reason='https://github.com/pycurl/pycurl/issues/729')
    def test_multi_remove_handle(self):
        self.multi.add_handle(self.easy)
        self.multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
        self.socket_result = None
        self.multi.remove_handle(self.easy)
        assert self.socket_result is not None

    # (mid-transfer) easy.pause(PAUSE_ALL) must call SOCKETFUNCTION to remove sockets
    # (mid-transfer) easy.pause(PAUSE_CONT) must call TIMERFUNCTION to resume
    @pytest.mark.xfail(sys.platform == 'darwin', reason='https://github.com/pycurl/pycurl/issues/729')
    def test_easy_pause_unpause(self):
        self.partial_transfer()
        self.socket_result = None
        # libcurl will now inform us that we should remove some sockets
        self.easy.pause(pycurl.PAUSE_ALL)
        assert self.socket_result is not None
        self.socket_result = None
        self.timer_result = None
        # libcurl will now tell us to add those sockets and schedule a kickstart
        self.easy.pause(pycurl.PAUSE_CONT)
        assert self.socket_result is not None
        assert self.timer_result is not None

    # (mid-transfer) easy.close() must call SOCKETFUNCTION to remove sockets
    @pytest.mark.xfail(sys.platform == 'darwin', reason='https://github.com/pycurl/pycurl/issues/729')
    def test_easy_close(self):
        self.partial_transfer()
        self.socket_result = None
        self.easy.close()
        assert self.socket_result is not None
