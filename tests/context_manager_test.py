#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest

from . import appmanager
from . import localhost

setup_module, teardown_module = appmanager.setup(('app', 8380))

class ContextManagerTest(unittest.TestCase):
    def test_context_manager(self):
        with pycurl.Curl() as curl:
            curl.setopt(pycurl.URL, 'http://%s:8380/success' % localhost)
            curl.perform()
