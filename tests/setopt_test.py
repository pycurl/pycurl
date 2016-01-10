#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest
import nose.tools

from . import util

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

    def test_httpheader_list(self):
        self.curl.setopt(self.curl.HTTPHEADER, ['Accept:'])

    def test_httpheader_tuple(self):
        self.curl.setopt(self.curl.HTTPHEADER, ('Accept:',))

    def test_httpheader_unicode(self):
        self.curl.setopt(self.curl.HTTPHEADER, (u'Accept:',))

    @util.min_libcurl(7, 37, 0)
    def test_proxyheader_list(self):
        self.curl.setopt(self.curl.PROXYHEADER, ['Accept:'])

    @util.min_libcurl(7, 37, 0)
    def test_proxyheader_tuple(self):
        self.curl.setopt(self.curl.PROXYHEADER, ('Accept:',))

    @util.min_libcurl(7, 37, 0)
    def test_proxyheader_unicode(self):
        self.curl.setopt(self.curl.PROXYHEADER, (u'Accept:',))
