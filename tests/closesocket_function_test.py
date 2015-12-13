#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import os
import unittest
import pycurl

from . import util
from . import appmanager

setup_module, teardown_module = appmanager.setup(('app', 8380))

class ClosesocketFunctionTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
        self.curl.setopt(self.curl.URL, 'http://localhost:8380/success')
        self.curl.setopt(pycurl.FORBID_REUSE, True)

    def tearDown(self):
        self.curl.close()

    @util.min_libcurl(7, 21, 7)
    def test_closesocketfunction_ok(self):
        called = {}
        
        def closesocketfunction(curlfd):
            called['called'] = True
            os.close(curlfd)
            return 0

        self.curl.setopt(pycurl.CLOSESOCKETFUNCTION, closesocketfunction)

        self.curl.perform()
        assert called['called']

    @util.min_libcurl(7, 21, 7)
    def test_closesocketfunction_fail(self):
        called = {}
        
        def closesocketfunction(curlfd):
            called['called'] = True
            os.close(curlfd)
            return 1

        self.curl.setopt(pycurl.CLOSESOCKETFUNCTION, closesocketfunction)

        # no exception on errors, apparently
        self.curl.perform()
        assert called['called']

    @util.min_libcurl(7, 21, 7)
    def test_closesocketfunction_bogus_return(self):
        called = {}
        
        def closesocketfunction(curlfd):
            called['called'] = True
            os.close(curlfd)
            return 'bogus'

        self.curl.setopt(pycurl.CLOSESOCKETFUNCTION, closesocketfunction)

        # no exception on errors, apparently
        self.curl.perform()
        assert called['called']

class ClosesocketFunctionUnsetTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()

    @util.min_libcurl(7, 21, 7)
    def test_closesocketfunction_none(self):
        self.curl.setopt(pycurl.CLOSESOCKETFUNCTION, None)

    @util.min_libcurl(7, 21, 7)
    def test_closesocketfunction_unset(self):
        self.curl.unsetopt(pycurl.CLOSESOCKETFUNCTION)
