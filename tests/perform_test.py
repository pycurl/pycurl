#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import pycurl

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class PerformTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurl()

    def tearDown(self):
        self.curl.close()

    def test_perform_rb(self):
        self.curl.setopt(pycurl.URL, 'http://%s:8380/success' % localhost)
        body = self.curl.perform_rb()
        self.assertEqual(util.b('success'), body)

    def test_perform_rs(self):
        self.curl.setopt(pycurl.URL, 'http://%s:8380/success' % localhost)
        body = self.curl.perform_rs()
        self.assertEqual(util.u('success'), body)

    def test_perform_rb_utf8(self):
        self.curl.setopt(pycurl.URL, 'http://%s:8380/utf8_body' % localhost)
        body = self.curl.perform_rb()
        if util.py3:
            self.assertEqual('Дружба народов'.encode('utf8'), body)
        else:
            self.assertEqual('Дружба народов', body)

    def test_perform_rs_utf8(self):
        self.curl.setopt(pycurl.URL, 'http://%s:8380/utf8_body' % localhost)
        body = self.curl.perform_rs()
        self.assertEqual('Дружба народов', body)

    def test_perform_rb_invalid_utf8(self):
        self.curl.setopt(pycurl.URL, 'http://%s:8380/invalid_utf8_body' % localhost)
        body = self.curl.perform_rb()
        self.assertEqual(util.b('\xb3\xd2\xda\xcd\xd7'), body)

    @util.only_python2
    def test_perform_rs_invalid_utf8_python2(self):
        self.curl.setopt(pycurl.URL, 'http://%s:8380/invalid_utf8_body' % localhost)
        body = self.curl.perform_rs()
        self.assertEqual('\xb3\xd2\xda\xcd\xd7', body)

    @util.only_python3
    def test_perform_rs_invalid_utf8_python3(self):
        self.curl.setopt(pycurl.URL, 'http://%s:8380/invalid_utf8_body' % localhost)
        try:
            self.curl.perform_rs()
        except UnicodeDecodeError:
            pass
        else:
            self.fail('Should have raised')
