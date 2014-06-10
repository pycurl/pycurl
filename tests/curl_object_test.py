#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest

class CurlObjectTest(unittest.TestCase):
    def test_close(self):
        c = pycurl.Curl()
        c.close()
    
    def test_close_twice(self):
        c = pycurl.Curl()
        c.close()
        c.close()
