#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import pycurl
import unittest

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class FailonerrorTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurl()

    def tearDown(self):
        self.curl.close()

    # not sure what the actual min is but 7.26 is too old
    # and does not include status text, only the status code
    @util.min_libcurl(7, 38, 0)
    # no longer supported by libcurl: https://github.com/curl/curl/issues/6615
    @util.removed_in_libcurl(7, 75, 0)
    def test_failonerror(self):
        self.curl.setopt(pycurl.URL, 'http://%s:8380/status/403' % localhost)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEDATA, sio)
        self.curl.setopt(pycurl.FAILONERROR, True)
        #self.curl.setopt(pycurl.VERBOSE, True)
        try:
            self.curl.perform()
        except pycurl.error as e:
            self.assertEqual(pycurl.E_HTTP_RETURNED_ERROR, e.args[0])
            self.assertEqual('The requested URL returned error: 403 Forbidden', e.args[1])
            self.assertEqual(util.u('The requested URL returned error: 403 Forbidden'), self.curl.errstr())
            self.assertEqual(util.b('The requested URL returned error: 403 Forbidden'), self.curl.errstr_raw())
        else:
            self.fail('Should have raised pycurl.error')
    
    @util.only_python2
    # not sure what the actual min is but 7.26 is too old
    # and does not include status text, only the status code
    @util.min_libcurl(7, 38, 0)
    # no longer supported by libcurl: https://github.com/curl/curl/issues/6615
    @util.removed_in_libcurl(7, 75, 0)
    def test_failonerror_status_line_invalid_utf8_python2(self):
        self.curl.setopt(pycurl.URL, 'http://%s:8380/status_invalid_utf8' % localhost)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEDATA, sio)
        self.curl.setopt(pycurl.FAILONERROR, True)
        #self.curl.setopt(pycurl.VERBOSE, True)
        try:
            self.curl.perform()
        except pycurl.error as e:
            self.assertEqual(pycurl.E_HTTP_RETURNED_ERROR, e.args[0])
            self.assertEqual('The requested URL returned error: 555 \xb3\xd2\xda\xcd\xd7', e.args[1])
            self.assertEqual('The requested URL returned error: 555 \xb3\xd2\xda\xcd\xd7', self.curl.errstr())
            self.assertEqual('The requested URL returned error: 555 \xb3\xd2\xda\xcd\xd7', self.curl.errstr_raw())
        else:
            self.fail('Should have raised pycurl.error')

    @util.only_python3
    # not sure what the actual min is but 7.26 is too old
    # and does not include status text, only the status code
    @util.min_libcurl(7, 38, 0)
    # no longer supported by libcurl: https://github.com/curl/curl/issues/6615
    @util.removed_in_libcurl(7, 75, 0)
    def test_failonerror_status_line_invalid_utf8_python3(self):
        self.curl.setopt(pycurl.URL, 'http://%s:8380/status_invalid_utf8' % localhost)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEDATA, sio)
        self.curl.setopt(pycurl.FAILONERROR, True)
        #self.curl.setopt(pycurl.VERBOSE, True)
        try:
            self.curl.perform()
        except pycurl.error as e:
            self.assertEqual(pycurl.E_HTTP_RETURNED_ERROR, e.args[0])
            assert e.args[1].startswith('The requested URL returned error: 555 ')
            try:
                self.curl.errstr()
            except UnicodeDecodeError:
                pass
            else:
                self.fail('Should have raised')
            self.assertEqual(util.b('The requested URL returned error: 555 \xb3\xd2\xda\xcd\xd7'), self.curl.errstr_raw())
        else:
            self.fail('Should have raised pycurl.error')
