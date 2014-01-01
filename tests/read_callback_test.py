#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest
import sys
try:
    import json
except ImportError:
    import simplejson as json
try:
    import urllib.parse as urllib_parse
except ImportError:
    import urllib as urllib_parse

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

POSTFIELDS = {
    'field1':'value1',
    'field2':'value2 with blanks',
    'field3':'value3',
}
POSTSTRING = urllib_parse.urlencode(POSTFIELDS)

class DataProvider(object):
    def __init__(self, data):
        self.data = data
        self.finished = False

    def read_cb(self, size):
        assert len(self.data) <= size
        if not self.finished:
            self.finished = True
            return self.data
        else:
            # Nothing more to read
            return ""

class ReadCallbackTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_post_with_read_callback(self):
        d = DataProvider(POSTSTRING)
        self.curl.setopt(self.curl.URL, 'http://localhost:8380/postfields')
        self.curl.setopt(self.curl.POST, 1)
        self.curl.setopt(self.curl.POSTFIELDSIZE, len(POSTSTRING))
        self.curl.setopt(self.curl.READFUNCTION, d.read_cb)
        #self.curl.setopt(self.curl.VERBOSE, 1)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        
        actual = json.loads(sio.getvalue().decode())
        self.assertEqual(POSTFIELDS, actual)
    
    def test_post_with_read_callback_returning_bytes(self):
        self.check_bytes('world')
    
    def test_post_with_read_callback_returning_bytes_with_nulls(self):
        self.check_bytes("wor\0ld")
    
    def test_post_with_read_callback_returning_bytes_with_multibyte(self):
        self.check_bytes(util.u("Пушкин"))
    
    def check_bytes(self, poststring):
        data = poststring.encode('utf8')
        assert type(data) == util.binary_type
        d = DataProvider(data)
        
        self.curl.setopt(self.curl.URL, 'http://localhost:8380/raw_utf8')
        self.curl.setopt(self.curl.POST, 1)
        self.curl.setopt(self.curl.HTTPHEADER, ['Content-Type: application/octet-stream'])
        # length of bytes
        self.curl.setopt(self.curl.POSTFIELDSIZE, len(data))
        self.curl.setopt(self.curl.READFUNCTION, d.read_cb)
        #self.curl.setopt(self.curl.VERBOSE, 1)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        
        # json should be ascii
        actual = json.loads(sio.getvalue().decode('ascii'))
        self.assertEqual(poststring, actual)
    
    def test_post_with_read_callback_returning_unicode(self):
        self.check_unicode(util.u('world'))
    
    def test_post_with_read_callback_returning_unicode_with_nulls(self):
        self.check_unicode(util.u("wor\0ld"))
    
    def test_post_with_read_callback_returning_unicode_with_multibyte(self):
        try:
            self.check_unicode(util.u("Пушкин"))
            # prints:
            # UnicodeEncodeError: 'ascii' codec can't encode characters in position 6-11: ordinal not in range(128)
        except pycurl.error:
            err, msg = sys.exc_info()[1].args
            # we expect pycurl.E_WRITE_ERROR as the response
            self.assertEqual(pycurl.E_ABORTED_BY_CALLBACK, err)
            self.assertEqual('operation aborted by callback', msg)
    
    def check_unicode(self, poststring):
        assert type(poststring) == util.text_type
        d = DataProvider(poststring)
        
        self.curl.setopt(self.curl.URL, 'http://localhost:8380/raw_utf8')
        self.curl.setopt(self.curl.POST, 1)
        self.curl.setopt(self.curl.HTTPHEADER, ['Content-Type: application/octet-stream'])
        self.curl.setopt(self.curl.POSTFIELDSIZE, len(poststring))
        self.curl.setopt(self.curl.READFUNCTION, d.read_cb)
        #self.curl.setopt(self.curl.VERBOSE, 1)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        
        # json should be ascii
        actual = json.loads(sio.getvalue().decode('ascii'))
        self.assertEqual(poststring, actual)
