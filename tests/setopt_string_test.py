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
        self.curl = util.default_test_curl()

    def tearDown(self):
        self.curl.close()

    def test_setopt_string(self):
        self.curl.setopt_string(pycurl.URL, 'http://localhost:8380/success')
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        self.assertEqual('success', sio.getvalue().decode())

    @nose.tools.raises(TypeError)
    def test_setopt_string_integer(self):
        self.curl.setopt_string(pycurl.VERBOSE, True)
