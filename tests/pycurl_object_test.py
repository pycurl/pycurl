#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et

import pycurl
import unittest
import sys

class PycurlObjectTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_set_attribute(self):
        assert not hasattr(self.curl, 'attr')
        self.curl.attr = 1
        assert hasattr(self.curl, 'attr')
    
    def test_get_attribute(self):
        assert not hasattr(self.curl, 'attr')
        self.curl.attr = 1
        self.assertEqual(1, self.curl.attr)
    
    def test_delete_attribute(self):
        assert not hasattr(self.curl, 'attr')
        self.curl.attr = 1
        self.assertEqual(1, self.curl.attr)
        assert hasattr(self.curl, 'attr')
        del self.curl.attr
        assert not hasattr(self.curl, 'attr')
