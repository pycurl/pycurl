#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et

import pycurl
import unittest
import nose.plugins.skip

from . import util

class CertinfoTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_certinfo_option(self):
        # CURLOPT_CERTINFO was introduced in libcurl-7.19.1
        if util.pycurl_version_less_than(7, 19, 1):
            raise nose.plugins.skip.SkipTest('libcurl < 7.19.1')
        
        assert hasattr(pycurl, 'OPT_CERTINFO')
    
    def test_request_without_certinfo(self):
        # CURLOPT_CERTINFO was introduced in libcurl-7.19.1
        if util.pycurl_version_less_than(7, 19, 1):
            raise nose.plugins.skip.SkipTest('libcurl < 7.19.1')
        
        self.curl.setopt(pycurl.URL, 'https://github.com/')
        sio = util.StringIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        assert 'GitHub' in sio.getvalue()
        
        certinfo = self.curl.getinfo(pycurl.INFO_CERTINFO)
        self.assertEqual([], certinfo)
    
    def test_request_with_certinfo(self):
        # CURLOPT_CERTINFO was introduced in libcurl-7.19.1
        if util.pycurl_version_less_than(7, 19, 1):
            raise nose.plugins.skip.SkipTest('libcurl < 7.19.1')
        
        self.curl.setopt(pycurl.URL, 'https://github.com/')
        sio = util.StringIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.setopt(pycurl.OPT_CERTINFO, 1)
        self.curl.perform()
        assert 'GitHub' in sio.getvalue()
        
        certinfo = self.curl.getinfo(pycurl.INFO_CERTINFO)
        assert len(certinfo) > 0
