#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest
import nose.plugins.attrib
import sys

@nose.plugins.attrib.attr('standalone')
class ReloadTest(unittest.TestCase):
    def test_reloading(self):
        reload(pycurl)
