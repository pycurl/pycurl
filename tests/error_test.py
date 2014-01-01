#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import sys
import unittest

class ErrorTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()

    def tearDown(self):
        self.curl.close()

    # error originating in libcurl
    def test_pycurl_error_libcurl(self):
        try:
            # perform without a url
            self.curl.perform()
        except pycurl.error:
            exc_type, exc = sys.exc_info()[:2]
            assert exc_type == pycurl.error
            # pycurl.error's arguments are libcurl errno and message
            self.assertEqual(2, len(exc.args))
            self.assertEqual(int, type(exc.args[0]))
            self.assertEqual(str, type(exc.args[1]))
            # unpack
            err, msg = exc.args
            self.assertEqual(pycurl.E_URL_MALFORMAT, err)
            # possibly fragile
            self.assertEqual('No URL set!', msg)
        else:
            self.fail('Expected pycurl.error to be raised')
    
    def test_pycurl_errstr_initially_empty(self):
        self.assertEqual('', self.curl.errstr())
    
    def test_pycurl_errstr_type(self):
        self.assertEqual('', self.curl.errstr())
        try:
            # perform without a url
            self.curl.perform()
        except pycurl.error:
            # might be fragile
            self.assertEqual('No URL set!', self.curl.errstr())
            # repeated checks do not clear value
            self.assertEqual('No URL set!', self.curl.errstr())
            # check the type - on all python versions
            self.assertEqual(str, type(self.curl.errstr()))
        else:
            self.fail('no exception')

    # pycurl raises standard library exceptions in some cases
    def test_pycurl_error_stdlib(self):
        try:
            # set an option of the wrong type
            self.curl.setopt(pycurl.WRITEFUNCTION, True)
        except TypeError:
            exc_type, exc = sys.exc_info()[:2]
        else:
            self.fail('Expected TypeError to be raised')

    # error originating in pycurl
    def test_pycurl_error_pycurl(self):
        try:
            # invalid option combination
            self.curl.setopt(pycurl.WRITEFUNCTION, lambda x: x)
            f = open(__file__)
            try:
                self.curl.setopt(pycurl.WRITEHEADER, f)
            finally:
                f.close()
        except pycurl.error:
            exc_type, exc = sys.exc_info()[:2]
            assert exc_type == pycurl.error
            # for non-libcurl errors, arguments are just the error string
            self.assertEqual(1, len(exc.args))
            self.assertEqual(str, type(exc.args[0]))
            self.assertEqual('cannot combine WRITEHEADER with WRITEFUNCTION.', exc.args[0])
        else:
            self.fail('Expected pycurl.error to be raised')
