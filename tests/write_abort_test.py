#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et

import os.path
import pycurl
import sys
import unittest

class WriteAbortTest(unittest.TestCase):
    def setUp(self):
        pycurl.global_init(pycurl.GLOBAL_DEFAULT)

    def tearDown(self):
        pycurl.global_cleanup()

    def test_write_abort(self):
        def write_cb(_):
            # this should cause pycurl.WRITEFUNCTION (without any range errors)
            return -1

        # download the script itself through the file:// protocol into write_cb
        c = pycurl.Curl()
        c.setopt(pycurl.URL, 'file://' + os.path.abspath(sys.argv[0]))
        c.setopt(pycurl.WRITEFUNCTION, write_cb)
        try:
            c.perform()
        except pycurl.error, (err, msg):
            # we expect pycurl.E_WRITE_ERROR as the response
            assert pycurl.E_WRITE_ERROR == err

        # no additional errors should be reported
        assert not hasattr(sys, 'last_value')

        c.close()
