#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest
import nose.plugins.skip

from . import util

class OptionConstantsTest(unittest.TestCase):
    # CURLOPT_USERNAME was introduced in libcurl-7.19.1
    @util.min_libcurl(7, 19, 1)
    def test_username(self):
        assert hasattr(pycurl, 'USERNAME')
        assert hasattr(pycurl, 'PASSWORD')
        assert hasattr(pycurl, 'PROXYUSERNAME')
        assert hasattr(pycurl, 'PROXYPASSWORD')
    
    # CURLOPT_DNS_SERVERS was introduced in libcurl-7.24.0
    @util.min_libcurl(7, 24, 0)
    def test_dns_servers(self):
        assert hasattr(pycurl, 'DNS_SERVERS')
        
        # Does not work unless libcurl was built against c-ares
        #c = pycurl.Curl()
        #c.setopt(c.DNS_SERVERS, '1.2.3.4')
        #c.close()

    # CURLOPT_POSTREDIR was introduced in libcurl-7.19.1
    @util.min_libcurl(7, 19, 1)
    def test_postredir(self):
        assert hasattr(pycurl, 'POSTREDIR')
        assert hasattr(pycurl, 'REDIR_POST_301')
        assert hasattr(pycurl, 'REDIR_POST_302')
        assert hasattr(pycurl, 'REDIR_POST_ALL')
    
    # CURLOPT_POSTREDIR was introduced in libcurl-7.19.1
    @util.min_libcurl(7, 19, 1)
    def test_postredir_setopt(self):
        curl = pycurl.Curl()
        curl.setopt(curl.POSTREDIR, curl.REDIR_POST_301)
        curl.close()
    
    # CURL_REDIR_POST_303 was introduced in libcurl-7.26.0
    @util.min_libcurl(7, 26, 0)
    def test_redir_post_303(self):
        assert hasattr(pycurl, 'REDIR_POST_303')

    # CURLOPT_POSTREDIR was introduced in libcurl-7.19.1
    @util.min_libcurl(7, 19, 1)
    def test_postredir_flags(self):
        self.assertEqual(pycurl.REDIR_POST_301, pycurl.REDIR_POST_ALL & pycurl.REDIR_POST_301)
        self.assertEqual(pycurl.REDIR_POST_302, pycurl.REDIR_POST_ALL & pycurl.REDIR_POST_302)

    # CURL_REDIR_POST_303 was introduced in libcurl-7.26.0
    @util.min_libcurl(7, 26, 0)
    def test_postredir_flags(self):
        self.assertEqual(pycurl.REDIR_POST_303, pycurl.REDIR_POST_ALL & pycurl.REDIR_POST_303)

    # HTTPAUTH_DIGEST_IE was introduced in libcurl-7.19.3
    @util.min_libcurl(7, 19, 3)
    def test_httpauth_digest_ie(self):
        assert hasattr(pycurl, 'HTTPAUTH_DIGEST_IE')

    # CURLE_OPERATION_TIMEDOUT was introduced in libcurl-7.10.2
    # to replace CURLE_OPERATION_TIMEOUTED
    def test_operation_timedout_constant(self):
        self.assertEqual(pycurl.E_OPERATION_TIMEDOUT, pycurl.E_OPERATION_TIMEOUTED)
    
    # CURLOPT_NOPROXY was introduced in libcurl-7.19.4
    @util.min_libcurl(7, 19, 4)
    def test_noproxy_setopt(self):
        curl = pycurl.Curl()
        curl.setopt(curl.NOPROXY, 'localhost')
        curl.close()
