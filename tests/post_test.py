#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et

import os.path
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
        self.check_post(send, expect, 'http://localhost:8380/postfields')
    
    def test_post_file(self):
        path = os.path.join(os.path.dirname(__file__), '..', 'README')
        with open(path) as f:
            contents = f.read()
        send = [
            #('field2', (pycurl.FORM_FILE, 'test_post.py', pycurl.FORM_FILE, 'test_post2.py')),
            ('field2', (pycurl.FORM_FILE, path)),
        ]
        expect = [{
            'name': 'field2',
            'filename': 'README',
            'data': contents,
        }]
        self.check_post(send, expect, 'http://localhost:8380/files')
    
    # XXX this test takes about a second to run, check keep-alives?
    def check_post(self, send, expect, endpoint):
        self.curl.setopt(pycurl.URL, endpoint)
        self.curl.setopt(pycurl.HTTPPOST, send)
        #self.curl.setopt(pycurl.VERBOSE, 1)
        sio = util.StringIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        body = sio.getvalue()
        returned_fields = json.loads(body)
        self.assertEqual(expect, returned_fields)
