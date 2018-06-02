#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import pycurl
import unittest
import sys

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class WriteToStringioTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurl()

    def tearDown(self):
        self.curl.close()

    def test_write_to_bytesio(self):
        self.curl.setopt(pycurl.URL, 'http://%s:8380/success' % localhost)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        self.assertEqual('success', sio.getvalue().decode())

    @util.only_python3
    def test_write_to_stringio(self):
        self.curl.setopt(pycurl.URL, 'http://%s:8380/success' % localhost)
        # stringio in python 3
        sio = util.StringIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        try:
            self.curl.perform()

            self.fail('Should have received a write error')
        except pycurl.error:
            err, msg = sys.exc_info()[1].args
            # we expect pycurl.E_WRITE_ERROR as the response
            assert pycurl.E_WRITE_ERROR == err
