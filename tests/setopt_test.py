#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest
import nose.tools

class SetoptTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_boolean_value(self):
        # expect no exceptions raised
        self.curl.setopt(pycurl.VERBOSE, True)
    
    def test_integer_value(self):
        # expect no exceptions raised
        self.curl.setopt(pycurl.VERBOSE, 1)
    
    @nose.tools.raises(TypeError)
    def test_string_value_for_integer_option(self):
        self.curl.setopt(pycurl.VERBOSE, "Hello, world!")
    
    def test_string_value(self):
        # expect no exceptions raised
        self.curl.setopt(pycurl.URL, 'http://hello.world')
    
    @nose.tools.raises(TypeError)
    def test_integer_value_for_string_option(self):
        self.curl.setopt(pycurl.URL, 1)
    
    @nose.tools.raises(TypeError)
    def test_float_value_for_integer_option(self):
        self.curl.setopt(pycurl.VERBOSE, 1.0)
    
    def test_list_value(self):
        # expect no exceptions raised
        self.curl.setopt(pycurl.HTTPHEADER, ['Accept:'])
