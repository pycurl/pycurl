#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et

import pycurl
import unittest
import io

from . import app
from . import runwsgi
from . import util

setup_module, teardown_module = runwsgi.app_runner_setup((app.app, 8380))

class WriteToStringioTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_get(self):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/success')
        sio = util.StringIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        self.assertEqual('success', sio.getvalue())
