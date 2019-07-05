#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest

from . import util

class InfoTest(unittest.TestCase):
    @util.only_ssl
    def test_ssl_engines(self):
        curl = pycurl.Curl()
        engines = curl.getinfo(curl.SSL_ENGINES)
        # Typical result:
        # - an empty list in some configurations
        # - ['rdrand', 'dynamic']
        self.assertEqual(type(engines), list)
        curl.close()
