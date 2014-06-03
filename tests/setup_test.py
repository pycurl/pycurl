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

def set_env(key, new_value):
    old_value = os.environ.get(key)
    if new_value is not None:
        os.environ[key] = new_value
    elif old_value is not None:
        del os.environ[key]
    else:
        # new and old values are None which mean the variable is not set
        pass
    return old_value

def reset_env(key, old_value):
    # empty string means environment variable was empty
    # None means it was not set
    if old_value is not None:
        os.environ[key] = old_value
    elif key in os.environ:
        del os.environ[key]

def using_curl_config(path, ssl_library=None):
    path = os.path.join(os.path.dirname(__file__), 'fake-curl', path)
    def decorator(fn):
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            old_path = set_env('PYCURL_CURL_CONFIG', path)
            old_ssl_library = set_env('PYCURL_SSL_LIBRARY', ssl_library)
            try:
                return fn(*args, **kwargs)
            finally:
                reset_env('PYCURL_CURL_CONFIG', old_path)
                reset_env('PYCURL_SSL_LIBRARY', old_ssl_library)
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
        assert 'crypto' not in config.libraries
    
    @using_curl_config('curl-config-libs-and-static-libs')
    def test_does_not_use_static_libs(self):
        config = pycurl_setup.ExtensionConfiguration()
        # should not link against any libraries from --static-libs if
        # --libs succeeded
        assert 'flurby' in config.libraries
        assert 'kzzert' not in config.libraries
    
    @using_curl_config('curl-config-ssl-in-libs')
    def test_ssl_in_libs(self):
        config = pycurl_setup.ExtensionConfiguration()
        # should link against openssl
        assert 'crypto' in config.libraries
    
    @using_curl_config('curl-config-ssl-in-static-libs')
    def test_ssl_in_static_libs(self):
        config = pycurl_setup.ExtensionConfiguration()
        # should link against openssl
        assert 'crypto' in config.libraries
    
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
        config = pycurl_setup.ExtensionConfiguration()
        # ssl define should be on
        assert 'HAVE_CURL_SSL' in config.define_symbols
    
    @using_curl_config('curl-config-ssl-feature-only')
    def test_ssl_feature_sets_ssl_define(self):
        config = pycurl_setup.ExtensionConfiguration()
        # ssl define should be on
        assert 'HAVE_CURL_SSL' in config.define_symbols
