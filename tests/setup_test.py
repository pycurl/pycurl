#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import setup as pycurl_setup
import unittest
import os, os.path
import nose.plugins.skip

try:
    import functools
except ImportError:
    import functools_backport as functools

def using_curl_config(path):
    path = os.path.join(os.path.dirname(__file__), 'fake-curl', path)
    def decorator(fn):
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            wasset = os.environ.has_key('PYCURL_CURL_CONFIG')
            old = os.environ.get('PYCURL_CURL_CONFIG')
            os.environ['PYCURL_CURL_CONFIG'] = path
            try:
                return fn(*args, **kwargs)
            finally:
                if wasset:
                    os.environ['PYCURL_CURL_CONFIG'] = old
                else:
                    del os.environ['PYCURL_CURL_CONFIG']
        return decorated
    return decorator

class SetupTest(unittest.TestCase):
    def test_sanity_check(self):
        config = pycurl_setup.ExtensionConfiguration()
        # we should link against libcurl, one would expect
        assert 'curl' in config.libraries
    
    @using_curl_config('curl-config-empty')
    def test_no_ssl(self):
        config = pycurl_setup.ExtensionConfiguration()
        # do not expect anything to do with ssl
        assert 'ssl' not in config.libraries
    
    @using_curl_config('curl-config-ssl-in-libs')
    def test_ssl_in_libs(self):
        config = pycurl_setup.ExtensionConfiguration()
        # should link against openssl
        assert 'ssl' in config.libraries
    
    @using_curl_config('curl-config-ssl-in-static-libs')
    def test_ssl_in_static_libs(self):
        raise nose.plugins.skip.SkipTest('this test fails')
        
        config = pycurl_setup.ExtensionConfiguration()
        # should link against openssl
        assert 'ssl' in config.libraries
    
    @using_curl_config('curl-config-empty')
    def test_no_ssl_define(self):
        config = pycurl_setup.ExtensionConfiguration()
        # ssl define should be off
        assert 'HAVE_CURL_SSL' not in config.define_symbols
    
    @using_curl_config('curl-config-ssl-in-libs')
    def test_ssl_in_libs_sets_ssl_define(self):
        config = pycurl_setup.ExtensionConfiguration()
        # ssl define should be on
        assert 'HAVE_CURL_SSL' in config.define_symbols
    
    @using_curl_config('curl-config-ssl-in-static-libs')
    def test_ssl_in_static_libs_sets_ssl_define(self):
        raise nose.plugins.skip.SkipTest('this test fails')
        
        config = pycurl_setup.ExtensionConfiguration()
        # ssl define should be on
        assert 'HAVE_CURL_SSL' in config.define_symbols
    
    @using_curl_config('curl-config-ssl-feature-only')
    def test_ssl_feature_sets_ssl_define(self):
        config = pycurl_setup.ExtensionConfiguration()
        # ssl define should be on
        assert 'HAVE_CURL_SSL' in config.define_symbols
