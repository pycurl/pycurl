#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import pycurl
import pytest
import unittest

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class SetoptTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurl()

    def tearDown(self):
        self.curl.close()

    def test_boolean_value(self):
        # expect no exceptions raised
        self.curl.setopt(pycurl.VERBOSE, True)

    def test_integer_value(self):
        # expect no exceptions raised
        self.curl.setopt(pycurl.VERBOSE, 1)

    def test_string_value_for_integer_option(self):
        with pytest.raises(TypeError):
            self.curl.setopt(pycurl.VERBOSE, "Hello, world!")

    def test_string_value(self):
        # expect no exceptions raised
        self.curl.setopt(pycurl.URL, 'http://hello.world')

    def test_integer_value_for_string_option(self):
        with pytest.raises(TypeError):
            self.curl.setopt(pycurl.URL, 1)

    def test_float_value_for_integer_option(self):
        with pytest.raises(TypeError):
            self.curl.setopt(pycurl.VERBOSE, 1.0)

    def test_httpheader_list(self):
        self.curl.setopt(self.curl.HTTPHEADER, ['Accept:'])

    def test_httpheader_tuple(self):
        self.curl.setopt(self.curl.HTTPHEADER, ('Accept:',))

    def test_httpheader_unicode(self):
        self.curl.setopt(self.curl.HTTPHEADER, (util.u('Accept:'),))

    def test_unset_httpheader(self):
        self.curl.setopt(self.curl.HTTPHEADER, ('x-test: foo',))
        self.curl.setopt(self.curl.URL, 'http://%s:8380/header?h=x-test' % localhost)
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
        self.curl.setopt(self.curl.URL, 'http://%s:8380/header?h=x-test' % localhost)
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

    # github issue #405
    def test_large_options(self):
        self.curl.setopt(self.curl.INFILESIZE, 3333858173)
        self.curl.setopt(self.curl.MAX_RECV_SPEED_LARGE, 3333858173)
        self.curl.setopt(self.curl.MAX_SEND_SPEED_LARGE, 3333858173)
        self.curl.setopt(self.curl.MAXFILESIZE, 3333858173)
        self.curl.setopt(self.curl.POSTFIELDSIZE, 3333858173)
        self.curl.setopt(self.curl.RESUME_FROM, 3333858173)
