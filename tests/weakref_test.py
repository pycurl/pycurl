#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import unittest
import weakref
import pycurl

class WeakrefTest(unittest.TestCase):
    def test_easy(self):
        c = pycurl.Curl()
        weakref.ref(c)
        c.close()
    
    def test_multi(self):
        m = pycurl.CurlMulti()
        weakref.ref(m)
        m.close()
    
    def test_share(self):
        s = pycurl.CurlShare()
        weakref.ref(s)
        s.close()
