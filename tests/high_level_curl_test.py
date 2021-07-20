#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
# uses the high level interface
import curl
import unittest

from . import appmanager

setup_module, teardown_module = appmanager.setup(('app', 8380))

class RelativeUrlTest(unittest.TestCase):
    def setUp(self):
        self.curl = curl.Curl('http://%s:8380/' % localhost)

    def tearDown(self):
        self.curl.close()

    def test_get(self):
        result = self.curl.get('/success')
        self.assertEqual('success', result.decode())

    def test_head(self):
        result = self.curl.head('/success')
        self.assertEqual('', result.decode())
        self.assertEqual(200, self.curl.info()['http-code'])

    def test_reuse(self):
        result = self.curl.get('/success')
        self.assertEqual('success', result.decode())

        result = self.curl.get('/success')
        self.assertEqual('success', result.decode())
