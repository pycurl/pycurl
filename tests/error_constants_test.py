#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest

from . import util

class ErrorConstantsTest(unittest.TestCase):
    @util.min_libcurl(7, 21, 5)
    def test_not_built_in(self):
        assert hasattr(pycurl, 'E_NOT_BUILT_IN')
    
    @util.min_libcurl(7, 24, 0)
    def test_ftp_accept_failed(self):
        assert hasattr(pycurl, 'E_FTP_ACCEPT_FAILED')
    
    @util.min_libcurl(7, 21, 5)
    def test_unknown_option(self):
        assert hasattr(pycurl, 'E_UNKNOWN_OPTION')
