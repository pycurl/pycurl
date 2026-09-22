#! /usr/bin/env python
# vi:ts=4:et

from io import StringIO

from . import util
import setup as pycurl_setup
import unittest
import os, os.path, sys
import functools

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

def using_curl_config(path, ssl_library=None, libcurl_dll=None):
    path = os.path.join(os.path.dirname(__file__), 'fake-curl', path)
    def decorator(fn):
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            old_path = set_env('PYCURL_CURL_CONFIG', path)
            old_ssl_library = set_env('PYCURL_SSL_LIBRARY', ssl_library)
            old_libcurl_dll = set_env('PYCURL_LIBCURL_DLL', libcurl_dll)
            try:
                return fn(*args, **kwargs)
            finally:
                reset_env('PYCURL_CURL_CONFIG', old_path)
                reset_env('PYCURL_SSL_LIBRARY', old_ssl_library)
                reset_env('PYCURL_LIBCURL_DLL', old_libcurl_dll)
        return decorated
    return decorator

def fake_libcurl_so(name):
    return os.path.join(os.path.dirname(__file__), 'fake-curl', 'libcurl', name)

def min_python_version(*spec):
    def decorator(fn):
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            if sys.version_info < spec:
                raise unittest.SkipTest('Minimum Python version %s required' % spec.join('.'))

            return fn(*args, **kwargs)
        return decorated
    return decorator

class SetupTest(unittest.TestCase):

    @util.only_unix
    def test_sanity_check(self):
        config = pycurl_setup.ExtensionConfiguration()
        # we should link against libcurl, one would expect
        assert 'curl' in config.libraries

    @util.only_unix
    @using_curl_config('curl-config-empty')
    def test_no_ssl(self):
        config = pycurl_setup.ExtensionConfiguration()
        # do not expect anything to do with ssl
        assert 'crypto' not in config.libraries

    @util.only_unix
    @using_curl_config('curl-config-libs-and-static-libs')
    def test_does_not_use_static_libs(self):
        config = pycurl_setup.ExtensionConfiguration()
        # should not link against any libraries from --static-libs if
        # --libs succeeded
        assert 'flurby' in config.libraries
        assert 'kzzert' not in config.libraries

    @util.only_unix
    @using_curl_config('curl-config-ssl-in-libs')
    def test_ssl_in_libs(self):
        config = pycurl_setup.ExtensionConfiguration()
        # should link against openssl
        assert 'crypto' in config.libraries

    @util.only_unix
    @using_curl_config('curl-config-ssl-in-static-libs')
    def test_ssl_in_static_libs(self):
        config = pycurl_setup.ExtensionConfiguration()
        # should link against openssl
        assert 'crypto' in config.libraries

    @util.only_unix
    @using_curl_config('curl-config-empty')
    def test_no_ssl_define(self):
        config = pycurl_setup.ExtensionConfiguration()
        # ssl define should be off
        assert 'HAVE_CURL_SSL' not in config.define_symbols

    @util.only_unix
    @using_curl_config('curl-config-ssl-in-libs')
    def test_ssl_in_libs_sets_ssl_define(self):
        config = pycurl_setup.ExtensionConfiguration()
        # ssl define should be on
        assert 'HAVE_CURL_SSL' in config.define_symbols

    @util.only_unix
    @using_curl_config('curl-config-ssl-in-static-libs')
    def test_ssl_in_static_libs_sets_ssl_define(self):
        config = pycurl_setup.ExtensionConfiguration()
        # ssl define should be on
        assert 'HAVE_CURL_SSL' in config.define_symbols

    @util.only_unix
    @using_curl_config('curl-config-ssl-in-libs')
    def test_ssl_feature_sets_ssl_define(self):
        config = pycurl_setup.ExtensionConfiguration()
        # ssl define should be on
        assert 'HAVE_CURL_SSL' in config.define_symbols

    @util.only_unix
    @using_curl_config('curl-config-ssl-feature-only')
    def test_ssl_feature_only(self):
        saved_stderr = sys.stderr
        sys.stderr = captured_stderr = StringIO()
        try:
            config = pycurl_setup.ExtensionConfiguration()
        finally:
            sys.stderr = saved_stderr
        # ssl define should be on
        assert 'HAVE_CURL_SSL' in config.define_symbols
        # and a warning message
        assert 'Warning: libcurl is configured to use SSL, but we have \
not been able to determine which SSL backend it is using.' in captured_stderr.getvalue()

    @util.only_unix
    @using_curl_config('curl-config-ssl-feature-only', libcurl_dll=fake_libcurl_so('with_openssl.so'))
    def test_libcurl_ssl_openssl(self):
        config = pycurl_setup.ExtensionConfiguration()
        # openssl should be detected
        assert 'HAVE_CURL_SSL' in config.define_symbols
        assert 'HAVE_CURL_OPENSSL' in config.define_symbols
        assert 'crypto' in config.libraries

        assert 'HAVE_CURL_GNUTLS' not in config.define_symbols
        assert 'HAVE_CURL_NSS' not in config.define_symbols

    @util.only_unix
    @using_curl_config('curl-config-ssl-feature-only', libcurl_dll=fake_libcurl_so('with_gnutls.so'))
    def test_libcurl_ssl_gnutls(self):
        config = pycurl_setup.ExtensionConfiguration()
        # gnutls should be detected
        assert 'HAVE_CURL_SSL' in config.define_symbols
        assert 'HAVE_CURL_GNUTLS' in config.define_symbols
        assert 'gnutls' in config.libraries

        assert 'HAVE_CURL_OPENSSL' not in config.define_symbols
        assert 'HAVE_CURL_NSS' not in config.define_symbols

    @util.only_unix
    @using_curl_config('curl-config-ssl-feature-only', libcurl_dll=fake_libcurl_so('with_nss.so'))
    def test_libcurl_ssl_nss(self):
        config = pycurl_setup.ExtensionConfiguration()
        # nss should be detected
        assert 'HAVE_CURL_SSL' in config.define_symbols
        assert 'HAVE_CURL_NSS' in config.define_symbols
        assert 'ssl3' in config.libraries

        assert 'HAVE_CURL_OPENSSL' not in config.define_symbols
        assert 'HAVE_CURL_GNUTLS' not in config.define_symbols

    @util.only_unix
    @using_curl_config('curl-config-empty', libcurl_dll=fake_libcurl_so('with_unknown_ssl.so'))
    def test_libcurl_ssl_unrecognized(self):
        config = pycurl_setup.ExtensionConfiguration()
        assert 'HAVE_CURL_SSL' not in config.define_symbols
        assert 'HAVE_CURL_OPENSSL' not in config.define_symbols
        assert 'HAVE_CURL_GNUTLS' not in config.define_symbols
        assert 'HAVE_CURL_NSS' not in config.define_symbols

    @util.only_unix
    @using_curl_config('curl-config-empty', libcurl_dll=fake_libcurl_so('with_openssl.so'))
    def test_no_ssl_feature_with_libcurl_dll(self):
        config = pycurl_setup.ExtensionConfiguration()
        # openssl should not be detected
        assert 'HAVE_CURL_SSL' not in config.define_symbols
        assert 'HAVE_CURL_OPENSSL' not in config.define_symbols
        assert 'crypto' not in config.libraries

    @util.only_unix
    @using_curl_config('curl-config-ssl-feature-only', ssl_library='openssl')
    def test_with_openssl_library(self):
        config = pycurl_setup.ExtensionConfiguration()
        assert 'HAVE_CURL_SSL' in config.define_symbols
        assert 'HAVE_CURL_OPENSSL' in config.define_symbols
        assert 'crypto' in config.libraries

        assert 'HAVE_CURL_GNUTLS' not in config.define_symbols
        assert 'HAVE_CURL_NSS' not in config.define_symbols

    @util.only_unix
    @using_curl_config('curl-config-ssl-feature-only', ssl_library='gnutls')
    def test_with_gnutls_library(self):
        config = pycurl_setup.ExtensionConfiguration()
        assert 'HAVE_CURL_SSL' in config.define_symbols
        assert 'HAVE_CURL_GNUTLS' in config.define_symbols
        assert 'gnutls' in config.libraries

        assert 'HAVE_CURL_OPENSSL' not in config.define_symbols
        assert 'HAVE_CURL_NSS' not in config.define_symbols

    @util.only_unix
    @using_curl_config('curl-config-ssl-feature-only', ssl_library='nss')
    def test_with_nss_library(self):
        config = pycurl_setup.ExtensionConfiguration()
        assert 'HAVE_CURL_SSL' in config.define_symbols
        assert 'HAVE_CURL_NSS' in config.define_symbols
        assert 'ssl3' in config.libraries

        assert 'HAVE_CURL_OPENSSL' not in config.define_symbols
        assert 'HAVE_CURL_GNUTLS' not in config.define_symbols

    @util.only_unix
    @using_curl_config('curl-config-empty', ssl_library='openssl')
    def test_no_ssl_feature_with_ssl(self):
        old_stderr = sys.stderr
        sys.stderr = captured_stderr = StringIO()

        try:
            config = pycurl_setup.ExtensionConfiguration()
            # openssl should not be detected
            assert 'HAVE_CURL_SSL' not in config.define_symbols
            assert 'HAVE_CURL_OPENSSL' not in config.define_symbols
            assert 'crypto' not in config.libraries
        finally:
            sys.stderr = old_stderr

        self.assertEqual("Warning: SSL backend specified manually but libcurl does not use SSL",
            captured_stderr.getvalue().strip())
