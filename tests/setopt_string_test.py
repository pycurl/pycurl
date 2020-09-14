#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import pytest
from . import localhost
import unittest

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class SetoptTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurl()

    def tearDown(self):
        self.curl.close()

    def test_setopt_string(self):
        self.curl.setopt_string(pycurl.URL, 'http://%s:8380/success' % localhost)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        self.assertEqual('success', sio.getvalue().decode())

    def test_setopt_string_integer(self):
        with pytest.raises(TypeError):
            self.curl.setopt_string(pycurl.VERBOSE, True)
