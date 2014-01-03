#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest
import nose.tools
try:
    import json
except ImportError:
    import simplejson as json

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class SetoptUnicodeTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_ascii_string(self):
        self.check('p=test', 'test')
    
    @nose.tools.raises(UnicodeEncodeError)
    def test_unicode_string(self):
        self.check(util.u('p=Москва'), util.u('Москва'))
    
    def test_unicode_encoded(self):
        self.check(util.u('p=Москва').encode('utf8'), util.u('Москва'))
    
    def check(self, send, expected):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/param_utf8_hack')
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.setopt(pycurl.POSTFIELDS, send)
        self.curl.perform()
        self.assertEqual(expected, sio.getvalue().decode('utf-8'))
