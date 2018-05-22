#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

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

    def test_failonerror(self):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/status/403')
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEDATA, sio)
        self.curl.setopt(pycurl.FAILONERROR, True)
        #self.curl.setopt(pycurl.VERBOSE, True)
        try:
            self.curl.perform()
        except pycurl.error as e:
            self.assertEqual(pycurl.E_HTTP_RETURNED_ERROR, e.args[0])
            self.assertEqual('The requested URL returned error: 403 Forbidden', e.args[1])
        else:
            self.fail('Should have raised pycurl.error')
    
    @util.only_python2
    def test_failonerror_status_line_invalid_utf8_python2(self):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/status_invalid_utf8')
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEDATA, sio)
        self.curl.setopt(pycurl.FAILONERROR, True)
        #self.curl.setopt(pycurl.VERBOSE, True)
        try:
            self.curl.perform()
        except pycurl.error as e:
            self.assertEqual(pycurl.E_HTTP_RETURNED_ERROR, e.args[0])
            self.assertEqual('The requested URL returned error: 555 \xb3\xd2\xda\xcd\xd7', e.args[1])
        else:
            self.fail('Should have raised pycurl.error')

    @util.only_python3
    def test_failonerror_status_line_invalid_utf8_python3(self):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/status_invalid_utf8')
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEDATA, sio)
        self.curl.setopt(pycurl.FAILONERROR, True)
        #self.curl.setopt(pycurl.VERBOSE, True)
        try:
            self.curl.perform()
        except pycurl.error as e:
            self.assertEqual(pycurl.E_HTTP_RETURNED_ERROR, e.args[0])
            assert e.args[1].startswith('The requested URL returned error: 555 ')
        else:
            self.fail('Should have raised pycurl.error')
