#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import unittest
import pycurl

from . import util
from . import appmanager

setup_module, teardown_module = appmanager.setup(('app', 8380))

class XferinfoCbTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurl()
        self.curl.setopt(self.curl.URL, 'http://%s:8380/long_pause' % localhost)

    def tearDown(self):
        self.curl.close()

    @util.min_libcurl(7, 32, 0)
    def test_xferinfo_cb(self):
        all_args = []

        def xferinfofunction(*args):
            all_args.append(args)

        self.curl.setopt(pycurl.XFERINFOFUNCTION, xferinfofunction)
        self.curl.setopt(pycurl.NOPROGRESS, False)

        self.curl.perform()
        assert len(all_args) > 0
        for args in all_args:
            assert len(args) == 4
            for arg in args:
                assert isinstance(arg, util.long_int)

    @util.min_libcurl(7, 32, 0)
    def test_sockoptfunction_fail(self):
        called = {}

        def xferinfofunction(*args):
            called['called'] = True
            return -1

        self.curl.setopt(pycurl.XFERINFOFUNCTION, xferinfofunction)
        self.curl.setopt(pycurl.NOPROGRESS, False)

        try:
            self.curl.perform()
            self.fail('should have raised')
        except pycurl.error as e:
            assert e.args[0] in [pycurl.E_ABORTED_BY_CALLBACK], \
                'Unexpected pycurl error code %s' % e.args[0]
        assert called['called']

    @util.min_libcurl(7, 32, 0)
    def test_sockoptfunction_exception(self):
        called = {}

        def xferinfofunction(*args):
            called['called'] = True
            raise ValueError

        self.curl.setopt(pycurl.XFERINFOFUNCTION, xferinfofunction)
        self.curl.setopt(pycurl.NOPROGRESS, False)

        try:
            self.curl.perform()
            self.fail('should have raised')
        except pycurl.error as e:
            assert e.args[0] in [pycurl.E_ABORTED_BY_CALLBACK], \
                'Unexpected pycurl error code %s' % e.args[0]
        assert called['called']
