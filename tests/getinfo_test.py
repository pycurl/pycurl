#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class GetinfoTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_getinfo(self):
        self.make_request()
        
        self.assertEqual(200, self.curl.getinfo(pycurl.HTTP_CODE))
        assert type(self.curl.getinfo(pycurl.TOTAL_TIME)) is float
        assert self.curl.getinfo(pycurl.TOTAL_TIME) > 0
        assert self.curl.getinfo(pycurl.TOTAL_TIME) < 1
        assert type(self.curl.getinfo(pycurl.SPEED_DOWNLOAD)) is float
        assert self.curl.getinfo(pycurl.SPEED_DOWNLOAD) > 0
        self.assertEqual(7, self.curl.getinfo(pycurl.SIZE_DOWNLOAD))
        self.assertEqual('http://localhost:8380/success', self.curl.getinfo(pycurl.EFFECTIVE_URL))
        self.assertEqual('text/html; charset=utf-8', self.curl.getinfo(pycurl.CONTENT_TYPE).lower())
        assert type(self.curl.getinfo(pycurl.NAMELOOKUP_TIME)) is float
        assert self.curl.getinfo(pycurl.NAMELOOKUP_TIME) > 0
        assert self.curl.getinfo(pycurl.NAMELOOKUP_TIME) < 1
        self.assertEqual(0, self.curl.getinfo(pycurl.REDIRECT_TIME))
        self.assertEqual(0, self.curl.getinfo(pycurl.REDIRECT_COUNT))
        # time not requested
        self.assertEqual(-1, self.curl.getinfo(pycurl.INFO_FILETIME))
    
    @util.min_libcurl(7, 21, 0)
    def test_primary_port_etc(self):
        self.make_request()
        assert type(self.curl.getinfo(pycurl.PRIMARY_PORT)) is int
        assert type(self.curl.getinfo(pycurl.LOCAL_IP)) is str
        assert type(self.curl.getinfo(pycurl.LOCAL_PORT)) is int
    
    def make_request(self):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/success')
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        self.assertEqual('success', sio.getvalue().decode())
