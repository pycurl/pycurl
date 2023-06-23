#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest

from . import util

class VersionConstantsTest(unittest.TestCase):
    def test_ipv6(self):
        assert hasattr(pycurl, 'VERSION_IPV6')

    def test_kerberos4(self):
        assert hasattr(pycurl, 'VERSION_KERBEROS4')

    @util.min_libcurl(7, 40, 0)
    def test_kerberos5(self):
        assert hasattr(pycurl, 'VERSION_KERBEROS5')

    def test_ssl(self):
        assert hasattr(pycurl, 'VERSION_SSL')

    def test_libz(self):
        assert hasattr(pycurl, 'VERSION_LIBZ')

    def test_ntlm(self):
        assert hasattr(pycurl, 'VERSION_NTLM')

    def test_gssnegotiate(self):
        assert hasattr(pycurl, 'VERSION_GSSNEGOTIATE')

    def test_debug(self):
        assert hasattr(pycurl, 'VERSION_DEBUG')

    @util.min_libcurl(7, 19, 6)
    def test_curldebug(self):
        assert hasattr(pycurl, 'VERSION_CURLDEBUG')

    def test_asynchdns(self):
        assert hasattr(pycurl, 'VERSION_ASYNCHDNS')

    def test_spnego(self):
        assert hasattr(pycurl, 'VERSION_SPNEGO')

    def test_largefile(self):
        assert hasattr(pycurl, 'VERSION_LARGEFILE')

    def test_idn(self):
        assert hasattr(pycurl, 'VERSION_IDN')

    def test_sspi(self):
        assert hasattr(pycurl, 'VERSION_SSPI')

    @util.min_libcurl(7, 38, 0)
    def test_gssapi(self):
        assert hasattr(pycurl, 'VERSION_GSSAPI')

    def test_conv(self):
        assert hasattr(pycurl, 'VERSION_CONV')

    @util.min_libcurl(7, 21, 4)
    def test_tlsauth_srp(self):
        assert hasattr(pycurl, 'VERSION_TLSAUTH_SRP')

    @util.min_libcurl(7, 22, 0)
    def test_ntlm_wb(self):
        assert hasattr(pycurl, 'VERSION_NTLM_WB')

    @util.min_libcurl(7, 33, 0)
    def test_http2(self):
        assert hasattr(pycurl, 'VERSION_HTTP2')

    @util.min_libcurl(7, 40, 0)
    def test_unix_sockets(self):
        assert hasattr(pycurl, 'VERSION_UNIX_SOCKETS')

    @util.min_libcurl(7, 47, 0)
    def test_psl(self):
        assert hasattr(pycurl, 'VERSION_PSL')

    @util.min_libcurl(7, 52, 0)
    def test_https_proxy(self):
        assert hasattr(pycurl, 'VERSION_HTTPS_PROXY')

    @util.min_libcurl(7, 56, 0)
    def test_multi_ssl(self):
        assert hasattr(pycurl, 'VERSION_MULTI_SSL')

    @util.min_libcurl(7, 57, 0)
    def test_brotli(self):
        assert hasattr(pycurl, 'VERSION_BROTLI')

    @util.min_libcurl(7, 64, 1)
    def test_altsvc(self):
        assert hasattr(pycurl, 'VERSION_ALTSVC')

    @util.min_libcurl(7, 66, 0)
    def test_http3(self):
        assert hasattr(pycurl, 'VERSION_HTTP3')

    @util.min_libcurl(7, 72, 0)
    def test_unicode(self):
        assert hasattr(pycurl, 'VERSION_UNICODE')

    @util.min_libcurl(7, 72, 0)
    def test_zstd(self):
        assert hasattr(pycurl, 'VERSION_ZSTD')

    @util.min_libcurl(7, 74, 0)
    def test_hsts(self):
        assert hasattr(pycurl, 'VERSION_HSTS')
