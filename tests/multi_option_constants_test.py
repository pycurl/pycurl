#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest

from . import util

class MultiOptionConstantsTest(unittest.TestCase):
    def test_option_constant_on_pycurl(self):
        assert hasattr(pycurl, 'M_PIPELINING')

    def test_option_constant_on_curlmulti(self):
        m = pycurl.CurlMulti()
        assert hasattr(m, 'M_PIPELINING')

    @util.min_libcurl(7, 30, 0)
    def test_multi_pipeline_opts(self):
        assert hasattr(pycurl, 'M_MAX_HOST_CONNECTIONS')
        assert hasattr(pycurl, 'M_MAX_PIPELINE_LENGTH')
        assert hasattr(pycurl, 'M_CONTENT_LENGTH_PENALTY_SIZE')
        assert hasattr(pycurl, 'M_CHUNK_LENGTH_PENALTY_SIZE')
        assert hasattr(pycurl, 'M_MAX_TOTAL_CONNECTIONS')
        m = pycurl.CurlMulti()
        m.setopt(pycurl.M_MAX_HOST_CONNECTIONS, 2)
        m.setopt(pycurl.M_MAX_PIPELINE_LENGTH, 2)
        m.setopt(pycurl.M_CONTENT_LENGTH_PENALTY_SIZE, 2)
        m.setopt(pycurl.M_CHUNK_LENGTH_PENALTY_SIZE, 2)
        m.setopt(pycurl.M_MAX_TOTAL_CONNECTIONS, 2)
        m.close()
