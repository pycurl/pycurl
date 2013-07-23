# -*- coding: iso-8859-1 -*-

import pycurl
import unittest

from . import app
from . import runwsgi

setup_module, teardown_module = runwsgi.app_runner_setup((app.app, 8380))

class ResolveTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_resolve(self):
        self.curl.setopt(pycurl.URL, 'http://p.localhost:8380/success')
        self.curl.setopt(pycurl.RESOLVE, ['p.localhost:8380:127.0.0.1'])
        self.curl.perform()
        self.assertEqual(200, self.curl.getinfo(pycurl.RESPONSE_CODE))
