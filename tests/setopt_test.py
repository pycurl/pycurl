#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest
import nose.tools

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

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
        self.curl.setopt(self.curl.HTTPHEADER, (util.u('Accept:'),))

    def test_unset_httpheader(self):
        self.curl.setopt(self.curl.HTTPHEADER, ('x-test: foo',))
        self.curl.setopt(self.curl.URL, 'http://localhost:8380/header?h=x-test')
        io = util.BytesIO()
        self.curl.setopt(self.curl.WRITEDATA, io)
        self.curl.perform()
        self.assertEquals(util.b('foo'), io.getvalue())

        self.curl.unsetopt(self.curl.HTTPHEADER)
        io = util.BytesIO()
        self.curl.setopt(self.curl.WRITEDATA, io)
        self.curl.perform()
        self.assertEquals(util.b(''), io.getvalue())

    def test_set_httpheader_none(self):
        self.curl.setopt(self.curl.HTTPHEADER, ('x-test: foo',))
        self.curl.setopt(self.curl.URL, 'http://localhost:8380/header?h=x-test')
        io = util.BytesIO()
        self.curl.setopt(self.curl.WRITEDATA, io)
        self.curl.perform()
        self.assertEquals(util.b('foo'), io.getvalue())

        self.curl.setopt(self.curl.HTTPHEADER, None)
        io = util.BytesIO()
        self.curl.setopt(self.curl.WRITEDATA, io)
        self.curl.perform()
        self.assertEquals(util.b(''), io.getvalue())

    @util.min_libcurl(7, 37, 0)
    def test_proxyheader_list(self):
        self.curl.setopt(self.curl.PROXYHEADER, ['Accept:'])

    @util.min_libcurl(7, 37, 0)
    def test_proxyheader_tuple(self):
        self.curl.setopt(self.curl.PROXYHEADER, ('Accept:',))

    @util.min_libcurl(7, 37, 0)
    def test_proxyheader_unicode(self):
        self.curl.setopt(self.curl.PROXYHEADER, (util.u('Accept:'),))

    @util.min_libcurl(7, 37, 0)
    def test_unset_proxyheader(self):
        self.curl.unsetopt(self.curl.PROXYHEADER)

    @util.min_libcurl(7, 37, 0)
    def test_set_proxyheader_none(self):
        self.curl.setopt(self.curl.PROXYHEADER, None)

    def test_unset_encoding(self):
        self.curl.unsetopt(self.curl.ENCODING)

    def test_resume_from_large(self):
        # gh #405
        self.curl.setopt(self.curl.RESUME_FROM, 3333858173)
