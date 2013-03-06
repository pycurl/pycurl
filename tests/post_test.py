#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et

import pycurl
import unittest
import io
import json
try:
    import urllib.parse as urllib_parse
except ImportError:
    import urllib as urllib_parse

from . import app
from . import runwsgi
from . import util

setup_module, teardown_module = runwsgi.app_runner_setup((app.app, 8380))

class PostTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_post_single_field(self):
        pf = {'field1': 'value1'}
        self.urlencode_and_check(pf)
    
    def test_post_multiple_fields(self):
        pf = {'field1':'value1', 'field2':'value2 with blanks', 'field3':'value3'}
        self.urlencode_and_check(pf)
    
    def test_post_fields_with_ampersand(self):
        pf = {'field1':'value1', 'field2':'value2 with blanks and & chars',
              'field3':'value3'}
        self.urlencode_and_check(pf)
    
    def urlencode_and_check(self, pf):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/postfields')
        self.curl.setopt(pycurl.POSTFIELDS, urllib_parse.urlencode(pf))
        #self.curl.setopt(pycurl.VERBOSE, 1)
        sio = util.StringIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        body = sio.getvalue()
        returned_fields = json.loads(body)
        self.assertEqual(pf, returned_fields)
    
    def test_post_with_null_byte(self):
        send = [
            ('field3', (pycurl.FORM_CONTENTS, 'this is wei\000rd, but null-bytes are okay'))
        ]
        expect = {
            'field3': 'this is wei\000rd, but null-bytes are okay',
        }
        self.check_post(send, expect)
    
    def check_post(self, send, expect):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/postfields')
        self.curl.setopt(pycurl.HTTPPOST, send)
        #self.curl.setopt(pycurl.VERBOSE, 1)
        sio = util.StringIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        body = sio.getvalue()
        returned_fields = json.loads(body)
        self.assertEqual(expect, returned_fields)
