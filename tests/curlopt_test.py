#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et

import pycurl
import unittest
import nose.plugins.skip

from . import util

class CurloptTest(unittest.TestCase):
    def test_username(self):
        # CURLOPT_USERNAME was introduced in libcurl-7.19.1
        if util.pycurl_version_less_than(7, 19, 1):
            raise nose.plugins.skip.SkipTest('libcurl < 7.19.1')
        
        assert hasattr(pycurl, 'USERNAME')
        assert hasattr(pycurl, 'PASSWORD')
        assert hasattr(pycurl, 'PROXYUSERNAME')
        assert hasattr(pycurl, 'PROXYPASSWORD')
    
    def test_dns_servers(self):
        # CURLOPT_DNS_SERVERS was introduced in libcurl-7.24.0
        if util.pycurl_version_less_than(7, 24, 0):
            raise nose.plugins.skip.SkipTest('libcurl < 7.24.0')
        
        assert hasattr(pycurl, 'DNS_SERVERS')
        
        # Does not work unless libcurl was built against c-ares
        #c = pycurl.Curl()
        #c.setopt(c.DNS_SERVERS, '1.2.3.4')
        #c.close()
