#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest

from . import util

class SeekFunctionConstantsTest(unittest.TestCase):
    # numeric value is understood by older libcurls but
    # the constant is only defined in 7.19.5+
    @util.min_libcurl(7, 19, 5)
    def test_ok(self):
        curl = pycurl.Curl()
        self.assertEqual(0, curl.SEEKFUNC_OK)
        curl.close()
    
    # numeric value is understood by older libcurls but
    # the constant is only defined in 7.19.5+
    @util.min_libcurl(7, 19, 5)
    def test_fail(self):
        curl = pycurl.Curl()
        self.assertEqual(1, curl.SEEKFUNC_FAIL)
        curl.close()
    
    @util.min_libcurl(7, 19, 5)
    def test_cantseek(self):
        curl = pycurl.Curl()
        self.assertEqual(2, curl.SEEKFUNC_CANTSEEK)
        curl.close()
