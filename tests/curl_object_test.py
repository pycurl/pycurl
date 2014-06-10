#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest
import nose.tools

class CurlObjectTest(unittest.TestCase):
    def test_close(self):
        c = pycurl.Curl()
        c.close()
    
    def test_close_twice(self):
        c = pycurl.Curl()
        c.close()
        c.close()
    
    # positional arguments are rejected
    @nose.tools.raises(TypeError)
    def test_positional_arguments(self):
        c = pycurl.Curl(1)
    
    # keyword arguments are rejected
    @nose.tools.raises(TypeError)
    def test_keyword_arguments(self):
        c = pycurl.Curl(a=1)
