#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import sys
import pycurl
import unittest

from . import util

class MultiOptionConstantsTest(unittest.TestCase):
    def setUp(self):
        super(MultiOptionConstantsTest, self).setUp()

        self.m = pycurl.CurlMulti()

    def tearDown(self):
        super(MultiOptionConstantsTest, self).tearDown()

        self.m.close()

    def test_option_constant_on_pycurl(self):
        assert hasattr(pycurl, 'M_PIPELINING')

    def test_option_constant_on_curlmulti(self):
        assert hasattr(self.m, 'M_PIPELINING')

    @util.min_libcurl(7, 43, 0)
    def test_pipe_constants(self):
        self.m.setopt(self.m.M_PIPELINING, self.m.PIPE_NOTHING)
        self.m.setopt(self.m.M_PIPELINING, self.m.PIPE_HTTP1)
        self.m.setopt(self.m.M_PIPELINING, self.m.PIPE_MULTIPLEX)

    @util.min_libcurl(7, 30, 0)
    def test_multi_pipeline_opts(self):
        assert hasattr(pycurl, 'M_MAX_HOST_CONNECTIONS')
        assert hasattr(pycurl, 'M_MAX_PIPELINE_LENGTH')
        assert hasattr(pycurl, 'M_CONTENT_LENGTH_PENALTY_SIZE')
        assert hasattr(pycurl, 'M_CHUNK_LENGTH_PENALTY_SIZE')
        assert hasattr(pycurl, 'M_MAX_TOTAL_CONNECTIONS')
        self.m.setopt(pycurl.M_MAX_HOST_CONNECTIONS, 2)
        self.m.setopt(pycurl.M_MAX_PIPELINE_LENGTH, 2)
        self.m.setopt(pycurl.M_CONTENT_LENGTH_PENALTY_SIZE, 2)
        self.m.setopt(pycurl.M_CHUNK_LENGTH_PENALTY_SIZE, 2)
        self.m.setopt(pycurl.M_MAX_TOTAL_CONNECTIONS, 2)

    @util.min_libcurl(7, 30, 0)
    def test_multi_pipelining_site_bl(self):
        self.check_multi_charpp_option(self.m.M_PIPELINING_SITE_BL)

    @util.min_libcurl(7, 30, 0)
    def test_multi_pipelining_server_bl(self):
        self.check_multi_charpp_option(self.m.M_PIPELINING_SERVER_BL)

    def check_multi_charpp_option(self, option):
        input = [util.b('test1'), util.b('test2')]
        self.m.setopt(option, input)
        input = [util.u('test1'), util.u('test2')]
        self.m.setopt(option, input)
        self.m.setopt(option, [])
        input = (util.b('test1'), util.b('test2'))
        self.m.setopt(option, input)
        input = (util.u('test1'), util.u('test2'))
        self.m.setopt(option, input)
        self.m.setopt(option, ())

        try:
            self.m.setopt(option, 1)
            self.fail('expected to raise')
        except TypeError:
            exc = sys.exc_info()[1]
            assert 'integers are not supported for this option' in str(exc)
