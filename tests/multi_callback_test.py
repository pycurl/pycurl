#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import pycurl
import unittest

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class MultiCallbackTest(unittest.TestCase):
    def setUp(self):
        self.easy = util.DefaultCurl()
        self.easy.setopt(pycurl.URL, 'http://%s:8380/success' % localhost)
        self.multi = pycurl.CurlMulti()
        self.multi.setopt(pycurl.M_SOCKETFUNCTION, self.socket_callback)
        self.multi.setopt(pycurl.M_TIMERFUNCTION, self.timer_callback)
        self.timer_result = None
        self.socket_result = None
        self.socket_action = None

    def tearDown(self):
        self.multi.close()
        self.easy.close()

    def socket_callback(self, ev_bitmask, sock_fd, multi, data):
        self.socket_result = (sock_fd, ev_bitmask)
        if ev_bitmask & pycurl.POLL_REMOVE:
            pass
        else:
            self.socket_action = (sock_fd, ev_bitmask)

    def timer_callback(self, timeout_ms):
        self.timer_result = timeout_ms
        self.socket_action = (pycurl.SOCKET_TIMEOUT, 0)

    # multi.socket_action must call both SOCKETFUNCTION and TIMERFUNCTION at
    # various points during the transfer (at least at the start and end)
    def test_multi_socket_action(self):
        self.multi.add_handle(self.easy)
        self.timer_result = None
        self.socket_result = None
        while self.multi.socket_action(*self.socket_action)[1]:
            # Without real event loop we just use blocking select call instead
            self.multi.select(0.1)
        # both callbacks should be invoked multiple times by socket_action
        assert self.socket_result is not None
        assert self.timer_result is not None

    # multi.add_handle must call TIMERFUNCTION to schedule a kick-start
    def test_multi_add_handle(self):
        assert self.timer_result == None
        self.multi.add_handle(self.easy)
        assert self.timer_result is not None

    # (mid-transfer) multi.remove_handle must call SOCKETFUNCTION to remove sockets
    def test_multi_remove_handle(self):
        self.multi.add_handle(self.easy)
        while self.multi.socket_action(*self.socket_action)[1]:
            if self.socket_result:
                # libcurl informed us about new sockets
                break
            # Without real event loop we just use blocking select call instead
            self.multi.select(0.1)
        self.socket_result = None
        # libcurl will now inform us that we should remove those sockets
        self.multi.remove_handle(self.easy)
        assert self.socket_result is not None
    
    # (mid-transfer) easy.pause(PAUSE_ALL) must call SOCKETFUNCTION to remove sockets
    # (mid-transfer) easy.pause(PAUSE_CONT) must call TIMERFUNCTION to resume
    def test_easy_pause_unpause(self):
        self.multi.add_handle(self.easy)
        while self.multi.socket_action(*self.socket_action)[1]:
            if self.socket_result:
                # libcurl informed us about new sockets
                break
            # Without real event loop we just use blocking select call instead
            self.multi.select(0.1)
        self.socket_result = None
        # libcurl will now inform us that we should remove those sockets
        self.easy.pause(pycurl.PAUSE_ALL)
        assert self.socket_result is not None
        self.timer_result = None
        # libcurl will now tell us to schedule a kickstart
        self.easy.pause(pycurl.PAUSE_CONT)
        assert self.timer_result is not None

    # (mid-transfer) easy.close() must call SOCKETFUNCTION to remove sockets
    # NOTE: doing easy.close() during transfer is considered wrong,
    # but libcurl still invokes callbacks to inform your event loop
    def test_easy_close(self):
        self.multi.add_handle(self.easy)
        while self.multi.socket_action(*self.socket_action)[1]:
            if self.socket_result:
                # libcurl informed us about new sockets
                break
            # Without real event loop we just use blocking select call instead
            self.multi.select(0.1)
        self.socket_result = None
        # libcurl will now inform us that we should remove those sockets
        self.easy.close()
        assert self.socket_result is not None
