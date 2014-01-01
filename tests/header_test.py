#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest
import nose.tools

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

# NB: HTTP RFC requires headers to be latin1 encoded, which we violate.
# See the comments under /header_utf8 route in app.py.

class HeaderTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_ascii_string_header(self):
        self.check('x-test-header: ascii', 'ascii')
    
    def test_ascii_unicode_header(self):
        self.check(util.u('x-test-header: ascii'), 'ascii')
    
    # on python 2 unicode is accepted in strings because strings are byte strings
    @util.only_python3
    @nose.tools.raises(UnicodeEncodeError)
    def test_unicode_string_header(self):
        self.check('x-test-header: Москва', 'Москва')
    
    @nose.tools.raises(UnicodeEncodeError)
    def test_unicode_unicode_header(self):
        self.check(util.u('x-test-header: Москва'), util.u('Москва'))
    
    def test_encoded_unicode_header(self):
        self.check(util.u('x-test-header: Москва').encode('utf-8'), util.u('Москва'))
    
    def check(self, send, expected):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/header_utf8?h=x-test-header')
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.setopt(pycurl.HTTPHEADER, [send])
        self.curl.perform()
        self.assertEqual(expected, sio.getvalue().decode('utf-8'))
