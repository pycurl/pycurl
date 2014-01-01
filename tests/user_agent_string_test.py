#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import unittest
import pycurl

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class UserAgentStringTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_pycurl_user_agent_string(self):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/header?h=user-agent')
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        user_agent = sio.getvalue().decode()
        assert user_agent.startswith('PycURL/')
        assert 'libcurl/' in user_agent, 'User agent did not include libcurl/: %s' % user_agent
