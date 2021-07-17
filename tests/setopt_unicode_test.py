#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import pycurl
import pytest
import unittest

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class SetoptUnicodeTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurl()

    def tearDown(self):
        self.curl.close()

    def test_ascii_string(self):
        self.check('p=test', 'test')

    def test_unicode_string(self):
        with pytest.raises(UnicodeEncodeError):
            self.check(util.u('p=Москва'), util.u('Москва'))

    def test_unicode_encoded(self):
        self.check(util.u('p=Москва').encode('utf8'), util.u('Москва'))

    def check(self, send, expected):
        self.curl.setopt(pycurl.URL, 'http://%s:8380/param_utf8_hack' % localhost)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.setopt(pycurl.POSTFIELDS, send)
        self.curl.perform()
        self.assertEqual(expected, sio.getvalue().decode('utf-8'))
