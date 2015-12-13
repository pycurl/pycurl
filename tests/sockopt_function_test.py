#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import unittest
import pycurl

from . import util
from . import appmanager

setup_module, teardown_module = appmanager.setup(('app', 8380))

class SockoptFunctionTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
        self.curl.setopt(self.curl.URL, 'http://localhost:8380/success')

    def tearDown(self):
        self.curl.close()

    def test_sockoptfunction_ok(self):
        called = {}
        
        def sockoptfunction(curlfd, purpose):
            called['called'] = True
            return 0

        self.curl.setopt(pycurl.SOCKOPTFUNCTION, sockoptfunction)

        self.curl.perform()
        assert called['called']

    def test_sockoptfunction_fail(self):
        called = {}
        
        def sockoptfunction(curlfd, purpose):
            called['called'] = True
            return 1

        self.curl.setopt(pycurl.SOCKOPTFUNCTION, sockoptfunction)

        try:
            self.curl.perform()
            self.fail('should have raised')
        except pycurl.error as e:
            assert e.args[0] in [pycurl.E_ABORTED_BY_CALLBACK, pycurl.E_COULDNT_CONNECT], \
                'Unexpected pycurl error code %s' % e.args[0]
        assert called['called']

    def test_sockoptfunction_bogus_return(self):
        called = {}
        
        def sockoptfunction(curlfd, purpose):
            called['called'] = True
            return 'bogus'

        self.curl.setopt(pycurl.SOCKOPTFUNCTION, sockoptfunction)

        try:
            self.curl.perform()
            self.fail('should have raised')
        except pycurl.error as e:
            assert e.args[0] in [pycurl.E_ABORTED_BY_CALLBACK, pycurl.E_COULDNT_CONNECT], \
                'Unexpected pycurl error code %s' % e.args[0]
        assert called['called']

    @util.min_libcurl(7, 28, 0)
    def test_socktype_accept(self):
        assert hasattr(pycurl, 'SOCKTYPE_ACCEPT')
        assert hasattr(self.curl, 'SOCKTYPE_ACCEPT')
    
    def test_socktype_ipcxn(self):
        assert hasattr(pycurl, 'SOCKTYPE_IPCXN')
        assert hasattr(self.curl, 'SOCKTYPE_IPCXN')

class SshKeyfunctionUnsetTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()

    def test_sockoptfunction_none(self):
        self.curl.setopt(pycurl.SOCKOPTFUNCTION, None)

    def test_sockoptfunction_unset(self):
        self.curl.unsetopt(pycurl.SOCKOPTFUNCTION)
