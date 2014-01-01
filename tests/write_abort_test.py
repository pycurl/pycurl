#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import os.path
import pycurl
import sys
import unittest

class WriteAbortTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()

    def tearDown(self):
        self.curl.close()

    def test_write_abort(self):
        def write_cb(_):
            # this should cause pycurl.WRITEFUNCTION (without any range errors)
            return -1

        try:
            # set when running full test suite if any earlier tests
            # failed in Python code called from C
            del sys.last_value
        except AttributeError:
            pass

        # download the script itself through the file:// protocol into write_cb
        self.curl.setopt(pycurl.URL, 'file://' + os.path.abspath(sys.argv[0]))
        self.curl.setopt(pycurl.WRITEFUNCTION, write_cb)
        try:
            self.curl.perform()
        except pycurl.error:
            err, msg = sys.exc_info()[1].args
            # we expect pycurl.E_WRITE_ERROR as the response
            assert pycurl.E_WRITE_ERROR == err

        # no additional errors should be reported
        assert not hasattr(sys, 'last_value')
