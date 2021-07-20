#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import flaky
import pycurl
import unittest

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class GetinfoTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurl()

    def tearDown(self):
        self.curl.close()

    @flaky.flaky(max_runs=3)
    def test_getinfo(self):
        self.make_request()

        self.assertEqual(200, self.curl.getinfo(pycurl.HTTP_CODE))
        self.assertEqual(200, self.curl.getinfo(pycurl.RESPONSE_CODE))
        assert type(self.curl.getinfo(pycurl.TOTAL_TIME)) is float
        assert type(self.curl.getinfo(pycurl.SPEED_DOWNLOAD)) is float
        assert self.curl.getinfo(pycurl.SPEED_DOWNLOAD) > 0
        self.assertEqual(7, self.curl.getinfo(pycurl.SIZE_DOWNLOAD))
        self.assertEqual('http://%s:8380/success' % localhost, self.curl.getinfo(pycurl.EFFECTIVE_URL))
        self.assertEqual('text/html; charset=utf-8', self.curl.getinfo(pycurl.CONTENT_TYPE).lower())
        assert type(self.curl.getinfo(pycurl.NAMELOOKUP_TIME)) is float
        assert self.curl.getinfo(pycurl.NAMELOOKUP_TIME) > 0
        assert self.curl.getinfo(pycurl.NAMELOOKUP_TIME) < 1
        self.assertEqual(0, self.curl.getinfo(pycurl.REDIRECT_TIME))
        self.assertEqual(0, self.curl.getinfo(pycurl.REDIRECT_COUNT))
        # time not requested
        self.assertEqual(-1, self.curl.getinfo(pycurl.INFO_FILETIME))

    # It seems that times are 0 on appveyor
    @util.only_unix
    @flaky.flaky(max_runs=3)
    def test_getinfo_times(self):
        self.make_request()

        self.assertEqual(200, self.curl.getinfo(pycurl.HTTP_CODE))
        self.assertEqual(200, self.curl.getinfo(pycurl.RESPONSE_CODE))
        assert type(self.curl.getinfo(pycurl.TOTAL_TIME)) is float
        assert self.curl.getinfo(pycurl.TOTAL_TIME) > 0
        assert self.curl.getinfo(pycurl.TOTAL_TIME) < 1

    @util.min_libcurl(7, 21, 0)
    def test_primary_port_etc(self):
        self.make_request()
        assert type(self.curl.getinfo(pycurl.PRIMARY_PORT)) is int
        assert type(self.curl.getinfo(pycurl.LOCAL_IP)) is str
        assert type(self.curl.getinfo(pycurl.LOCAL_PORT)) is int

    def make_request(self, path='/success', expected_body='success'):
        self.curl.setopt(pycurl.URL, 'http://%s:8380' % localhost + path)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        self.assertEqual(expected_body, sio.getvalue().decode())

    @util.only_python2
    def test_getinfo_cookie_invalid_utf8_python2(self):
        self.curl.setopt(self.curl.COOKIELIST, '')
        self.make_request('/set_cookie_invalid_utf8', 'cookie set')
        
        self.assertEqual(200, self.curl.getinfo(pycurl.HTTP_CODE))
        expected = "%s" % localhost + "\tFALSE\t/\tFALSE\t0\t\xb3\xd2\xda\xcd\xd7\t%96%A6g%9Ay%B0%A5g%A7tm%7C%95%9A"
        self.assertEqual([expected], self.curl.getinfo(pycurl.INFO_COOKIELIST))

    @util.only_python3
    def test_getinfo_cookie_invalid_utf8_python3(self):
        self.curl.setopt(self.curl.COOKIELIST, '')
        self.make_request('/set_cookie_invalid_utf8', 'cookie set')
        
        self.assertEqual(200, self.curl.getinfo(pycurl.HTTP_CODE))
        
        info = self.curl.getinfo(pycurl.INFO_COOKIELIST)
        domain, incl_subdomains, path, secure, expires, name, value = info[0].split("\t")
        self.assertEqual('\xb3\xd2\xda\xcd\xd7', name)

    def test_getinfo_raw_cookie_invalid_utf8(self):
        raise unittest.SkipTest('bottle converts to utf-8? try without it')
        
        self.curl.setopt(self.curl.COOKIELIST, '')
        self.make_request('/set_cookie_invalid_utf8', 'cookie set')
        
        self.assertEqual(200, self.curl.getinfo(pycurl.HTTP_CODE))
        expected = util.b("%s" % localhost + "\tFALSE\t/\tFALSE\t0\t\xb3\xd2\xda\xcd\xd7\t%96%A6g%9Ay%B0%A5g%A7tm%7C%95%9A")
        self.assertEqual([expected], self.curl.getinfo_raw(pycurl.INFO_COOKIELIST))

    @util.only_python2
    def test_getinfo_content_type_invalid_utf8_python2(self):
        self.make_request('/content_type_invalid_utf8', 'content type set')
        
        self.assertEqual(200, self.curl.getinfo(pycurl.HTTP_CODE))
        expected = '\xb3\xd2\xda\xcd\xd7'
        self.assertEqual(expected, self.curl.getinfo(pycurl.CONTENT_TYPE))

    @util.only_python3
    def test_getinfo_content_type_invalid_utf8_python3(self):
        self.make_request('/content_type_invalid_utf8', 'content type set')
        
        self.assertEqual(200, self.curl.getinfo(pycurl.HTTP_CODE))
        
        value = self.curl.getinfo(pycurl.CONTENT_TYPE)
        self.assertEqual('\xb3\xd2\xda\xcd\xd7', value)

    def test_getinfo_raw_content_type_invalid_utf8(self):
        raise unittest.SkipTest('bottle converts to utf-8? try without it')
        
        self.make_request('/content_type_invalid_utf8', 'content type set')
        
        self.assertEqual(200, self.curl.getinfo(pycurl.HTTP_CODE))
        expected = util.b('\xb3\xd2\xda\xcd\xd7')
        self.assertEqual(expected, self.curl.getinfo_raw(pycurl.CONTENT_TYPE))

    def test_getinfo_number(self):
        self.make_request()
        self.assertEqual(7, self.curl.getinfo(pycurl.SIZE_DOWNLOAD))

    def test_getinfo_raw_number(self):
        self.make_request()
        self.assertEqual(7, self.curl.getinfo_raw(pycurl.SIZE_DOWNLOAD))
