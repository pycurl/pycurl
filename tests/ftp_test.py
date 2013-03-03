#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et

import pycurl
import unittest

from . import util

class FtpTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_get_ftp(self):
        self.curl.setopt(pycurl.URL, 'ftp://localhost:8921')
        sio = util.StringIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        
        result = sio.getvalue()
        assert 'README' in result
        assert 'bin -> usr/bin' in result
    
    # XXX this test needs to be fixed
    def test_quote(self):
        self.curl.setopt(pycurl.URL, 'ftp://localhost:8921')
        sio = util.StringIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.setopt(pycurl.QUOTE, ['CWD pub'])
        self.curl.perform()
        
        result = sio.getvalue()
        assert 'README' in result
        assert 'bin -> usr/bin' in result
    
    def test_epsv(self):
        self.curl.setopt(pycurl.URL, 'ftp://localhost:8921')
        sio = util.StringIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.setopt(pycurl.FTP_USE_EPSV, 1)
        self.curl.perform()
        
        result = sio.getvalue()
        assert 'README' in result
        assert 'bin -> usr/bin' in result
