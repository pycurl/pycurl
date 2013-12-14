#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et

import pycurl
import unittest

class EasyTest(unittest.TestCase):
    def test_easy_close(self):
        c = pycurl.Curl()
        c.close()
