#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import unittest
import pycurl

class VersionTest(unittest.TestCase):
    def test_pycurl_presence_and_case(self):
        assert pycurl.version.startswith('PycURL/')
    
    def test_libcurl_presence(self):
        assert 'libcurl/' in pycurl.version
