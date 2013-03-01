#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et

import pycurl
import unittest
try:
    from cStringIO import StringIO
except ImportError:
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO

class RequestTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_perform_get(self):
        self.curl.setopt(pycurl.URL, 'http://localhost')
        self.curl.perform()
    
    def test_perform_get_with_write_function(self):
        self.curl.setopt(pycurl.URL, 'http://localhost')
        sio = StringIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        print(sio.getvalue())
