#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et

from __future__ import with_statement

import unittest
import pycurl
import tempfile

from . import app
from . import runwsgi
from . import util

setup_module, teardown_module = runwsgi.app_runner_setup((app.app, 8380))

class WriteToFileTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_get_to_file(self):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/success')
        with tempfile.NamedTemporaryFile() as f:
            self.curl.setopt(pycurl.WRITEFUNCTION, f.write)
            self.curl.perform()
            f.seek(0)
            body = f.read()
        self.assertEqual('success', body)
