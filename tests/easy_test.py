#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest

class EasyTest(unittest.TestCase):
    def test_easy_close(self):
        c = pycurl.Curl()
        c.close()
    
    def test_easy_close_twice(self):
        c = pycurl.Curl()
        c.close()
        c.close()
