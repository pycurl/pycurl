#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import pycurl
import pytest
import unittest

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
    def test_postredir_post_303(self):
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
        curl.setopt(curl.NOPROXY, localhost)
        curl.close()

    # CURLOPT_PROTOCOLS was introduced in libcurl-7.19.4
    @util.min_libcurl(7, 19, 4)
    def test_protocols_setopt(self):
        curl = pycurl.Curl()
        curl.setopt(curl.PROTOCOLS, curl.PROTO_ALL & ~curl.PROTO_HTTP)
        curl.close()

    # CURLOPT_REDIR_PROTOCOLS was introduced in libcurl-7.19.4
    @util.min_libcurl(7, 19, 4)
    def test_redir_protocols_setopt(self):
        curl = pycurl.Curl()
        curl.setopt(curl.PROTOCOLS, curl.PROTO_ALL & ~curl.PROTO_HTTP)
        curl.close()

    # CURLOPT_TFTP_BLKSIZE was introduced in libcurl-7.19.4
    @util.min_libcurl(7, 19, 4)
    def test_tftp_blksize_setopt(self):
        curl = pycurl.Curl()
        curl.setopt(curl.TFTP_BLKSIZE, 1024)
        curl.close()

    # CURLOPT_SOCKS5_GSSAPI_SERVICE was introduced in libcurl-7.19.4
    @util.min_libcurl(7, 19, 4)
    @pytest.mark.gssapi
    def test_socks5_gssapi_service_setopt(self):
        curl = pycurl.Curl()
        curl.setopt(curl.SOCKS5_GSSAPI_SERVICE, 'helloworld')
        curl.close()

    # CURLOPT_SOCKS5_GSSAPI_NEC was introduced in libcurl-7.19.4
    @util.min_libcurl(7, 19, 4)
    @pytest.mark.gssapi
    def test_socks5_gssapi_nec_setopt(self):
        curl = pycurl.Curl()
        curl.setopt(curl.SOCKS5_GSSAPI_NEC, True)
        curl.close()

    # CURLPROXY_HTTP_1_0 was introduced in libcurl-7.19.4
    @util.min_libcurl(7, 19, 4)
    def test_curlproxy_http_1_0_setopt(self):
        curl = pycurl.Curl()
        curl.setopt(curl.PROXYTYPE, curl.PROXYTYPE_HTTP_1_0)
        curl.close()

    # CURLOPT_SSH_KNOWNHOSTS was introduced in libcurl-7.19.6
    @util.min_libcurl(7, 19, 6)
    @util.guard_unknown_libcurl_option
    def test_ssh_knownhosts_setopt(self):
        curl = pycurl.Curl()
        curl.setopt(curl.SSH_KNOWNHOSTS, '/hello/world')
        curl.close()

    # CURLOPT_MAIL_FROM was introduced in libcurl-7.20.0
    @util.min_libcurl(7, 20, 0)
    def test_mail_from(self):
        curl = pycurl.Curl()
        curl.setopt(curl.MAIL_FROM, 'hello@world.com')
        curl.close()

    # CURLOPT_MAIL_RCPT was introduced in libcurl-7.20.0
    @util.min_libcurl(7, 20, 0)
    def test_mail_rcpt(self):
        curl = pycurl.Curl()
        curl.setopt(curl.MAIL_RCPT, ['hello@world.com', 'foo@bar.com'])
        curl.close()

    # CURLOPT_MAIL_AUTH was introduced in libcurl-7.25.0
    @util.min_libcurl(7, 25, 0)
    def test_mail_auth(self):
        curl = pycurl.Curl()
        curl.setopt(curl.MAIL_AUTH, 'hello@world.com')
        curl.close()

    @util.min_libcurl(7, 22, 0)
    @pytest.mark.gssapi
    def test_gssapi_delegation_options(self):
        curl = pycurl.Curl()
        curl.setopt(curl.GSSAPI_DELEGATION, curl.GSSAPI_DELEGATION_FLAG)
        curl.setopt(curl.GSSAPI_DELEGATION, curl.GSSAPI_DELEGATION_NONE)
        curl.setopt(curl.GSSAPI_DELEGATION, curl.GSSAPI_DELEGATION_POLICY_FLAG)
        curl.close()

    # SSLVERSION_DEFAULT causes CURLE_UNKNOWN_OPTION without SSL
    @util.only_ssl
    def test_sslversion_options(self):
        curl = pycurl.Curl()
        curl.setopt(curl.SSLVERSION, curl.SSLVERSION_DEFAULT)
        curl.setopt(curl.SSLVERSION, curl.SSLVERSION_TLSv1)
        curl.close()

    # SSLVERSION_SSLv* return CURLE_BAD_FUNCTION_ARGUMENT with curl-7.77.0
    @util.removed_in_libcurl(7, 77, 0)
    @util.only_ssl
    def test_legacy_sslversion_options(self):
        curl = pycurl.Curl()
        curl.setopt(curl.SSLVERSION, curl.SSLVERSION_SSLv2)
        curl.setopt(curl.SSLVERSION, curl.SSLVERSION_SSLv3)
        curl.close()

    @util.min_libcurl(7, 34, 0)
    # SSLVERSION_TLSv1_0 causes CURLE_UNKNOWN_OPTION without SSL
    @util.only_ssl
    def test_sslversion_7_34_0(self):
        curl = pycurl.Curl()
        curl.setopt(curl.SSLVERSION, curl.SSLVERSION_TLSv1_0)
        curl.setopt(curl.SSLVERSION, curl.SSLVERSION_TLSv1_1)
        curl.setopt(curl.SSLVERSION, curl.SSLVERSION_TLSv1_2)
        curl.close()

    @util.min_libcurl(7, 41, 0)
    @util.only_ssl_backends('openssl', 'nss')
    def test_ssl_verifystatus(self):
        curl = pycurl.Curl()
        curl.setopt(curl.SSL_VERIFYSTATUS, True)
        curl.close()

    @util.min_libcurl(7, 43, 0)
    @pytest.mark.gssapi
    def test_proxy_service_name(self):
        curl = pycurl.Curl()
        curl.setopt(curl.PROXY_SERVICE_NAME, 'fakehttp')
        curl.close()

    @util.min_libcurl(7, 43, 0)
    @pytest.mark.gssapi
    def test_service_name(self):
        curl = pycurl.Curl()
        curl.setopt(curl.SERVICE_NAME, 'fakehttp')
        curl.close()

    @util.min_libcurl(7, 39, 0)
    @util.only_ssl
    def test_pinnedpublickey(self):
        curl = pycurl.Curl()
        curl.setopt(curl.PINNEDPUBLICKEY, '/etc/publickey.der')
        curl.close()

    @util.min_libcurl(7, 21, 0)
    def test_wildcardmatch(self):
        curl = pycurl.Curl()
        curl.setopt(curl.WILDCARDMATCH, '*')
        curl.close()

    @util.only_unix
    @util.min_libcurl(7, 40, 0)
    def test_unix_socket_path(self):
        curl = pycurl.Curl()
        curl.setopt(curl.UNIX_SOCKET_PATH, '/tmp/socket.sock')
        curl.close()

    @util.min_libcurl(7, 36, 0)
    @pytest.mark.http2
    def test_ssl_enable_alpn(self):
        curl = pycurl.Curl()
        curl.setopt(curl.SSL_ENABLE_ALPN, 1)
        curl.close()

    @util.min_libcurl(7, 36, 0)
    @pytest.mark.http2
    def test_ssl_enable_npn(self):
        curl = pycurl.Curl()
        curl.setopt(curl.SSL_ENABLE_NPN, 1)
        curl.close()

    @util.min_libcurl(7, 42, 0)
    @util.only_ssl_backends('nss')
    def test_ssl_falsestart(self):
        curl = pycurl.Curl()
        curl.setopt(curl.SSL_FALSESTART, 1)
        curl.close()

    def test_ssl_verifyhost(self):
        curl = pycurl.Curl()
        curl.setopt(curl.SSL_VERIFYHOST, 2)
        curl.close()

    def test_cainfo(self):
        curl = pycurl.Curl()
        curl.setopt(curl.CAINFO, '/bogus-cainfo')
        curl.close()

    @util.only_ssl
    def test_issuercert(self):
        curl = pycurl.Curl()
        curl.setopt(curl.ISSUERCERT, '/bogus-issuercert')
        curl.close()

    @util.only_ssl
    def test_capath(self):
        curl = pycurl.Curl()
        curl.setopt(curl.CAPATH, '/bogus-capath')
        curl.close()

    # CURLOPT_PROXY_CAPATH was introduced in libcurl-7.52.0
    @util.min_libcurl(7, 52, 0)
    @util.only_ssl
    def test_proxy_capath(self):
        curl = pycurl.Curl()
        curl.setopt(curl.PROXY_CAPATH, '/bogus-capath')
        curl.close()

    @util.min_libcurl(7, 52, 0)
    @util.only_ssl
    def test_proxy_sslcert(self):
        curl = pycurl.Curl()
        curl.setopt(curl.PROXY_SSLCERT, '/bogus-sslcert')
        curl.close()

    @util.min_libcurl(7, 52, 0)
    @util.only_ssl
    def test_proxy_sslcerttype(self):
        curl = pycurl.Curl()
        curl.setopt(curl.PROXY_SSLCERTTYPE, 'PEM')
        curl.close()

    @util.min_libcurl(7, 52, 0)
    @util.only_ssl
    def test_proxy_sslkey(self):
        curl = pycurl.Curl()
        curl.setopt(curl.PROXY_SSLKEY, '/bogus-sslkey')
        curl.close()

    @util.min_libcurl(7, 52, 0)
    @util.only_ssl
    def test_proxy_sslkeytype(self):
        curl = pycurl.Curl()
        curl.setopt(curl.PROXY_SSLKEYTYPE, 'PEM')
        curl.close()

    @util.min_libcurl(7, 52, 0)
    @util.only_ssl
    def test_proxy_ssl_verifypeer(self):
        curl = pycurl.Curl()
        curl.setopt(curl.PROXY_SSL_VERIFYPEER, 1)
        curl.close()

    @util.min_libcurl(7, 52, 0)
    @util.only_ssl
    def test_proxy_ssl_verifyhost(self):
        curl = pycurl.Curl()
        curl.setopt(curl.PROXY_SSL_VERIFYHOST, 2)
        curl.close()

    @util.only_ssl
    def test_crlfile(self):
        curl = pycurl.Curl()
        curl.setopt(curl.CRLFILE, '/bogus-crlfile')
        curl.close()

    @util.only_ssl
    def test_random_file(self):
        curl = pycurl.Curl()
        curl.setopt(curl.RANDOM_FILE, '/bogus-random')
        curl.close()

    @util.only_ssl_backends('openssl', 'gnutls')
    def test_egdsocket(self):
        curl = pycurl.Curl()
        curl.setopt(curl.EGDSOCKET, '/bogus-egdsocket')
        curl.close()

    @util.only_ssl
    def test_ssl_cipher_list(self):
        curl = pycurl.Curl()
        curl.setopt(curl.SSL_CIPHER_LIST, 'RC4-SHA:SHA1+DES')
        curl.close()

    @util.only_ssl
    def test_ssl_sessionid_cache(self):
        curl = pycurl.Curl()
        curl.setopt(curl.SSL_SESSIONID_CACHE, True)
        curl.close()

    def test_krblevel(self):
        curl = pycurl.Curl()
        curl.setopt(curl.KRBLEVEL, 'clear')
        curl.close()

    def test_krb4level(self):
        curl = pycurl.Curl()
        curl.setopt(curl.KRB4LEVEL, 'clear')
        curl.close()

    @util.min_libcurl(7, 25, 0)
    @util.only_ssl
    def test_ssl_options(self):
        curl = pycurl.Curl()
        curl.setopt(curl.SSL_OPTIONS, curl.SSLOPT_ALLOW_BEAST)
        curl.close()

    @util.min_libcurl(7, 44, 0)
    @util.only_ssl
    def test_ssl_option_no_revoke(self):
        curl = pycurl.Curl()
        curl.setopt(curl.SSL_OPTIONS, curl.SSLOPT_NO_REVOKE)
        curl.close()

class OptionConstantsSettingTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()

    def tearDown(self):
        self.curl.close()

    def test_append(self):
        self.curl.setopt(self.curl.APPEND, True)

    def test_cookiesession(self):
        self.curl.setopt(self.curl.COOKIESESSION, True)

    def test_dirlistonly(self):
        self.curl.setopt(self.curl.DIRLISTONLY, True)

    @util.only_ssl
    def test_keypasswd(self):
        self.curl.setopt(self.curl.KEYPASSWD, 'secret')

    @util.only_telnet
    def test_telnetoptions(self):
        self.curl.setopt(self.curl.TELNETOPTIONS, ('TTYPE=1', 'XDISPLOC=2'))

    @util.only_ssl
    def test_use_ssl(self):
        self.curl.setopt(self.curl.USE_SSL, self.curl.USESSL_NONE)
        self.curl.setopt(self.curl.USE_SSL, self.curl.USESSL_TRY)
        self.curl.setopt(self.curl.USE_SSL, self.curl.USESSL_CONTROL)
        self.curl.setopt(self.curl.USE_SSL, self.curl.USESSL_ALL)

    def test_encoding(self):
        # old name for ACCEPT_ENCODING
        self.curl.setopt(self.curl.ENCODING, "")
        self.curl.setopt(self.curl.ENCODING, "application/json")

    @util.min_libcurl(7, 21, 6)
    def test_accept_encoding(self):
        self.curl.setopt(self.curl.ACCEPT_ENCODING, "")
        self.curl.setopt(self.curl.ACCEPT_ENCODING, "application/json")

    @util.min_libcurl(7, 21, 6)
    def test_transfer_encoding(self):
        self.curl.setopt(self.curl.TRANSFER_ENCODING, True)

    @util.min_libcurl(7, 24, 0)
    def test_accepttimeout_ms(self):
        self.curl.setopt(self.curl.ACCEPTTIMEOUT_MS, 1000)

    @util.min_libcurl(7, 25, 0)
    def test_tcp_keepalive(self):
        self.curl.setopt(self.curl.TCP_KEEPALIVE, True)

    @util.min_libcurl(7, 25, 0)
    def test_tcp_keepidle(self):
        self.curl.setopt(self.curl.TCP_KEEPIDLE, 100)

    @util.min_libcurl(7, 25, 0)
    def test_tcp_keepintvl(self):
        self.curl.setopt(self.curl.TCP_KEEPINTVL, 100)

    @util.min_libcurl(7, 36, 0)
    def test_expect_100_timeout_ms(self):
        self.curl.setopt(self.curl.EXPECT_100_TIMEOUT_MS, 100)

    @util.min_libcurl(7, 37, 0)
    def test_headeropt(self):
        self.curl.setopt(self.curl.HEADEROPT, self.curl.HEADER_UNIFIED)
        self.curl.setopt(self.curl.HEADEROPT, self.curl.HEADER_SEPARATE)

    @util.min_libcurl(7, 42, 0)
    def test_path_as_is(self):
        self.curl.setopt(self.curl.PATH_AS_IS, True)

    @util.min_libcurl(7, 43, 0)
    def test_pipewait(self):
        self.curl.setopt(self.curl.PIPEWAIT, True)

    def test_http_version(self):
        self.curl.setopt(self.curl.HTTP_VERSION, self.curl.CURL_HTTP_VERSION_NONE)
        self.curl.setopt(self.curl.HTTP_VERSION, self.curl.CURL_HTTP_VERSION_1_0)
        self.curl.setopt(self.curl.HTTP_VERSION, self.curl.CURL_HTTP_VERSION_1_1)

    @util.min_libcurl(7, 33, 0)
    @pytest.mark.http2
    def test_http_version_2_0(self):
        self.curl.setopt(self.curl.HTTP_VERSION, self.curl.CURL_HTTP_VERSION_2_0)

    @util.min_libcurl(7, 43, 0)
    @pytest.mark.http2
    def test_http_version_2(self):
        self.curl.setopt(self.curl.HTTP_VERSION, self.curl.CURL_HTTP_VERSION_2)

    @util.min_libcurl(7, 47, 0)
    @pytest.mark.http2
    def test_http_version_2tls(self):
        self.curl.setopt(self.curl.HTTP_VERSION, self.curl.CURL_HTTP_VERSION_2TLS)

    @util.min_libcurl(7, 49, 0)
    @pytest.mark.http2
    def test_http_version_2prior_knowledge(self):
        self.curl.setopt(self.curl.HTTP_VERSION, self.curl.CURL_HTTP_VERSION_2_PRIOR_KNOWLEDGE)

    @util.min_libcurl(7, 21, 5)
    def test_sockopt_constants(self):
        assert self.curl.SOCKOPT_OK is not None
        assert self.curl.SOCKOPT_ERROR is not None
        assert self.curl.SOCKOPT_ALREADY_CONNECTED is not None

    @util.min_libcurl(7, 40, 0)
    def test_proto_smb(self):
        assert self.curl.PROTO_SMB is not None
        assert self.curl.PROTO_SMBS is not None

    # Apparently TLSAUTH_TYPE=SRP is an unknown option on appveyor
    @util.only_unix
    @util.min_libcurl(7, 21, 4)
    @util.only_ssl_backends('openssl', 'gnutls')
    def test_tlsauth(self):
        self.curl.setopt(self.curl.TLSAUTH_TYPE, "SRP")
        self.curl.setopt(self.curl.TLSAUTH_USERNAME, "test")
        self.curl.setopt(self.curl.TLSAUTH_PASSWORD, "test")

    @util.min_libcurl(7, 45, 0)
    def test_default_protocol(self):
        self.curl.setopt(self.curl.DEFAULT_PROTOCOL, "http")

    @util.min_libcurl(7, 20, 0)
    def test_ftp_use_pret(self):
        self.curl.setopt(self.curl.FTP_USE_PRET, True)

    @util.min_libcurl(7, 34, 0)
    def test_login_options(self):
        self.curl.setopt(self.curl.LOGIN_OPTIONS, 'AUTH=NTLM')

    @util.min_libcurl(7, 31, 0)
    def test_sasl_ir(self):
        self.curl.setopt(self.curl.SASL_IR, True)

    @util.min_libcurl(7, 33, 0)
    def test_xauth_bearer(self):
        self.curl.setopt(self.curl.XOAUTH2_BEARER, 'test')
        
    def test_cookielist_constants(self):
        self.assertEqual(pycurl.OPT_COOKIELIST, pycurl.COOKIELIST)
