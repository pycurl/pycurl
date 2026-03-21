import pycurl
import pytest

from . import localhost, util


# CURLOPT_USERNAME was introduced in libcurl-7.19.1
@util.min_libcurl(7, 19, 1)
def test_username():
    assert hasattr(pycurl, "USERNAME")
    assert hasattr(pycurl, "PASSWORD")
    assert hasattr(pycurl, "PROXYUSERNAME")
    assert hasattr(pycurl, "PROXYPASSWORD")


# CURLOPT_DNS_SERVERS was introduced in libcurl-7.24.0
@util.min_libcurl(7, 24, 0)
def test_dns_servers():
    assert hasattr(pycurl, "DNS_SERVERS")

    # Does not work unless libcurl was built against c-ares
    # c = pycurl.Curl()
    # c.setopt(c.DNS_SERVERS, '1.2.3.4')
    # c.close()


# CURLOPT_POSTREDIR was introduced in libcurl-7.19.1
@util.min_libcurl(7, 19, 1)
def test_postredir():
    assert hasattr(pycurl, "POSTREDIR")
    assert hasattr(pycurl, "REDIR_POST_301")
    assert hasattr(pycurl, "REDIR_POST_302")
    assert hasattr(pycurl, "REDIR_POST_ALL")


# CURLOPT_POSTREDIR was introduced in libcurl-7.19.1
@util.min_libcurl(7, 19, 1)
def test_postredir_setopt(curl):
    curl.setopt(curl.POSTREDIR, curl.REDIR_POST_301)


# CURL_REDIR_POST_303 was introduced in libcurl-7.26.0
@util.min_libcurl(7, 26, 0)
def test_redir_post_303():
    assert hasattr(pycurl, "REDIR_POST_303")


# CURLOPT_POSTREDIR was introduced in libcurl-7.19.1
@util.min_libcurl(7, 19, 1)
def test_postredir_flags():
    assert pycurl.REDIR_POST_301 == pycurl.REDIR_POST_ALL & pycurl.REDIR_POST_301
    assert pycurl.REDIR_POST_302 == pycurl.REDIR_POST_ALL & pycurl.REDIR_POST_302


# CURL_REDIR_POST_303 was introduced in libcurl-7.26.0
@util.min_libcurl(7, 26, 0)
def test_postredir_post_303():
    assert pycurl.REDIR_POST_303 == pycurl.REDIR_POST_ALL & pycurl.REDIR_POST_303


# HTTPAUTH_DIGEST_IE was introduced in libcurl-7.19.3
@util.min_libcurl(7, 19, 3)
def test_httpauth_digest_ie():
    assert hasattr(pycurl, "HTTPAUTH_DIGEST_IE")


# CURLE_OPERATION_TIMEDOUT was introduced in libcurl-7.10.2
# to replace CURLE_OPERATION_TIMEOUTED
def test_operation_timedout_constant():
    assert pycurl.E_OPERATION_TIMEDOUT == pycurl.E_OPERATION_TIMEOUTED


# CURLOPT_NOPROXY was introduced in libcurl-7.19.4
@util.min_libcurl(7, 19, 4)
def test_noproxy_setopt(curl):
    curl.setopt(curl.NOPROXY, localhost)


# CURLOPT_PROTOCOLS was introduced in libcurl-7.19.4
@util.min_libcurl(7, 19, 4)
def test_protocols_setopt(curl):
    curl.setopt(curl.PROTOCOLS, curl.PROTO_ALL & ~curl.PROTO_HTTP)


# CURLOPT_REDIR_PROTOCOLS was introduced in libcurl-7.19.4
@util.min_libcurl(7, 19, 4)
def test_redir_protocols_setopt(curl):
    curl.setopt(curl.PROTOCOLS, curl.PROTO_ALL & ~curl.PROTO_HTTP)


# CURLOPT_TFTP_BLKSIZE was introduced in libcurl-7.19.4
@util.min_libcurl(7, 19, 4)
def test_tftp_blksize_setopt(curl):
    curl.setopt(curl.TFTP_BLKSIZE, 1024)


# CURLOPT_SOCKS5_GSSAPI_SERVICE was introduced in libcurl-7.19.4
@util.min_libcurl(7, 19, 4)
@pytest.mark.gssapi
def test_socks5_gssapi_service_setopt(curl):
    curl.setopt(curl.SOCKS5_GSSAPI_SERVICE, "helloworld")


# CURLOPT_SOCKS5_GSSAPI_NEC was introduced in libcurl-7.19.4
@util.min_libcurl(7, 19, 4)
@util.only_gssapi
def test_socks5_gssapi_nec_setopt(curl):
    curl.setopt(curl.SOCKS5_GSSAPI_NEC, True)


# CURLPROXY_HTTP_1_0 was introduced in libcurl-7.19.4
@util.min_libcurl(7, 19, 4)
def test_curlproxy_http_1_0_setopt(curl):
    curl.setopt(curl.PROXYTYPE, curl.PROXYTYPE_HTTP_1_0)


# CURLOPT_SSH_KNOWNHOSTS was introduced in libcurl-7.19.6
@util.min_libcurl(7, 19, 6)
@util.guard_unknown_libcurl_option
def test_ssh_knownhosts_setopt(curl):
    curl.setopt(curl.SSH_KNOWNHOSTS, "/hello/world")


# CURLOPT_MAIL_FROM was introduced in libcurl-7.20.0
@util.min_libcurl(7, 20, 0)
def test_mail_from(curl):
    curl.setopt(curl.MAIL_FROM, "hello@world.com")


# CURLOPT_MAIL_RCPT was introduced in libcurl-7.20.0
@util.min_libcurl(7, 20, 0)
def test_mail_rcpt(curl):
    curl.setopt(curl.MAIL_RCPT, ["hello@world.com", "foo@bar.com"])


# CURLOPT_MAIL_AUTH was introduced in libcurl-7.25.0
@util.min_libcurl(7, 25, 0)
def test_mail_auth(curl):
    curl.setopt(curl.MAIL_AUTH, "hello@world.com")


@util.min_libcurl(7, 22, 0)
@util.only_gssapi
def test_gssapi_delegation_options(curl):
    curl.setopt(curl.GSSAPI_DELEGATION, curl.GSSAPI_DELEGATION_FLAG)
    curl.setopt(curl.GSSAPI_DELEGATION, curl.GSSAPI_DELEGATION_NONE)
    curl.setopt(curl.GSSAPI_DELEGATION, curl.GSSAPI_DELEGATION_POLICY_FLAG)


# SSLVERSION_DEFAULT causes CURLE_UNKNOWN_OPTION without SSL
@util.only_ssl
def test_sslversion_options(curl):
    curl.setopt(curl.SSLVERSION, curl.SSLVERSION_DEFAULT)
    curl.setopt(curl.SSLVERSION, curl.SSLVERSION_TLSv1)


# SSLVERSION_SSLv* return CURLE_BAD_FUNCTION_ARGUMENT with curl-7.77.0
@util.removed_in_libcurl(7, 77, 0)
@util.only_ssl
def test_legacy_sslversion_options(curl):
    curl.setopt(curl.SSLVERSION, curl.SSLVERSION_SSLv2)
    curl.setopt(curl.SSLVERSION, curl.SSLVERSION_SSLv3)


@util.min_libcurl(7, 34, 0)
# SSLVERSION_TLSv1_0 causes CURLE_UNKNOWN_OPTION without SSL
@util.only_ssl
def test_sslversion_7_34_0(curl):
    curl.setopt(curl.SSLVERSION, curl.SSLVERSION_TLSv1_0)
    curl.setopt(curl.SSLVERSION, curl.SSLVERSION_TLSv1_1)
    curl.setopt(curl.SSLVERSION, curl.SSLVERSION_TLSv1_2)


@util.min_libcurl(7, 41, 0)
@util.only_ssl_backends("openssl", "gnutls")
def test_ssl_verifystatus(curl):
    curl.setopt(curl.SSL_VERIFYSTATUS, True)


@util.min_libcurl(7, 43, 0)
@pytest.mark.gssapi
def test_proxy_service_name(curl):
    curl.setopt(curl.PROXY_SERVICE_NAME, "fakehttp")


@util.min_libcurl(7, 43, 0)
@pytest.mark.gssapi
def test_service_name(curl):
    curl.setopt(curl.SERVICE_NAME, "fakehttp")


@util.only_ssl_backends_with_min_libcurl(
    {
        "openssl": (7, 39, 0),
        "gnutls": (7, 39, 0),
        "wolfssl": (7, 43, 0),
        "mbedtls": (7, 47, 0),
        "schannel": (7, 58, 1),
    }
)
def test_pinnedpublickey(curl):
    curl.setopt(curl.PINNEDPUBLICKEY, "/etc/publickey.der")


@util.min_libcurl(7, 21, 0)
def test_wildcardmatch(curl):
    curl.setopt(curl.WILDCARDMATCH, "*")


@util.only_unix
@util.min_libcurl(7, 40, 0)
def test_unix_socket_path(curl):
    curl.setopt(curl.UNIX_SOCKET_PATH, "/tmp/socket.sock")


@util.min_libcurl(7, 36, 0)
@pytest.mark.http2
def test_ssl_enable_alpn(curl):
    curl.setopt(curl.SSL_ENABLE_ALPN, 1)


@util.min_libcurl(7, 36, 0)
@pytest.mark.http2
def test_ssl_enable_npn(curl):
    curl.setopt(curl.SSL_ENABLE_NPN, 1)


@util.min_libcurl(7, 42, 0)
@util.only_ssl
@util.guard_unknown_libcurl_option
def test_ssl_falsestart(curl):
    curl.setopt(curl.SSL_FALSESTART, 1)


def test_ssl_verifyhost(curl):
    curl.setopt(curl.SSL_VERIFYHOST, 2)


def test_cainfo(curl):
    curl.setopt(curl.CAINFO, "/bogus-cainfo")


@util.only_ssl_backends("openssl", "gnutls")
def test_issuercert(curl):
    curl.setopt(curl.ISSUERCERT, "/bogus-issuercert")


@util.only_ssl_backends("openssl", "gnutls", "mbedtls", "wolfssl")
def test_capath(curl):
    curl.setopt(curl.CAPATH, "/bogus-capath")


@util.only_ssl_backends_with_min_libcurl(
    {
        "openssl": (7, 77, 0),
        "schannel": (7, 77, 0),
        "mbedtls": (7, 81, 0),
        "rustls": (7, 82, 0),
        "wolfssl": (8, 2, 0),
        "gnutls": (8, 18, 0),
    }
)
def test_cainfo_blob(curl):
    curl.setopt(curl.CAINFO_BLOB, "bogus-cainfo-blob-as-str")
    curl.setopt(curl.CAINFO_BLOB, None)
    curl.setopt(curl.CAINFO_BLOB, b"bogus-cainfo-blob-as-bytes")
    curl.unsetopt(curl.CAINFO_BLOB)


@util.min_libcurl(7, 71, 0)
@util.only_ssl_backends("openssl", "schannel", "mbedtls", "wolfssl")
def test_sslcert_blob(curl):
    curl.setopt(curl.SSLCERT_BLOB, "bogus-sslcert-blob-as-str")
    curl.setopt(curl.SSLCERT_BLOB, None)
    curl.setopt(curl.SSLCERT_BLOB, b"bogus-sslcert-blob-as-bytes")
    curl.unsetopt(curl.SSLCERT_BLOB)


@util.min_libcurl(7, 71, 0)
@util.only_ssl_backends("openssl", "wolfssl")
def test_sslkey_blob(curl):
    curl.setopt(curl.SSLKEY_BLOB, "bogus-sslkey-blob-as-str")
    curl.setopt(curl.SSLKEY_BLOB, None)
    curl.setopt(curl.SSLKEY_BLOB, b"bogus-sslkey-blob-as-bytes")
    curl.unsetopt(curl.SSLKEY_BLOB)


@util.min_libcurl(7, 71, 0)
@util.only_ssl_backends("openssl")
def test_issuercert_blob(curl):
    curl.setopt(curl.ISSUERCERT_BLOB, "bogus-issuercert-blob-as-str")
    curl.setopt(curl.ISSUERCERT_BLOB, None)
    curl.setopt(curl.ISSUERCERT_BLOB, b"bogus-issuercert-blob-as-bytes")
    curl.unsetopt(curl.ISSUERCERT_BLOB)


# CURLOPT_PROXY_CAPATH was introduced in libcurl-7.52.0
@util.min_libcurl(7, 52, 0)
@util.only_ssl_backends("openssl", "gnutls", "mbedtls")
def test_proxy_capath(curl):
    curl.setopt(curl.PROXY_CAPATH, "/bogus-capath")


@util.min_libcurl(7, 52, 0)
@util.only_ssl
def test_proxy_cainfo(curl):
    curl.setopt(curl.PROXY_CAINFO, "/bogus-cainfo")


@util.min_libcurl(7, 77, 0)
@util.only_ssl_backends("openssl", "rustls", "schannel")
def test_proxy_cainfo_blob(curl):
    curl.setopt(curl.PROXY_CAINFO_BLOB, "bogus-cainfo-blob-as-str")
    curl.setopt(curl.PROXY_CAINFO_BLOB, None)
    curl.setopt(curl.PROXY_CAINFO_BLOB, b"bogus-cainfo-blob-as-bytes")
    curl.unsetopt(curl.PROXY_CAINFO_BLOB)


@util.min_libcurl(7, 52, 0)
@util.only_ssl_backends("openssl", "gnutls", "mbedtls")
def test_proxy_crlfile(curl):
    curl.setopt(curl.PROXY_CRLFILE, "/bogus-crlfile")


@util.min_libcurl(7, 52, 0)
@util.only_ssl
def test_proxy_sslcert(curl):
    curl.setopt(curl.PROXY_SSLCERT, "/bogus-sslcert")


@util.min_libcurl(7, 71, 0)
@util.only_ssl_backends("openssl", "schannel")
def test_proxy_sslcert_blob(curl):
    curl.setopt(curl.PROXY_SSLCERT_BLOB, "bogus-sslcert-blob-as-str")
    curl.setopt(curl.PROXY_SSLCERT_BLOB, None)
    curl.setopt(curl.PROXY_SSLCERT_BLOB, b"bogus-sslcert-blob-as-bytes")
    curl.unsetopt(curl.PROXY_SSLCERT_BLOB)


@util.min_libcurl(7, 52, 0)
@util.only_ssl
def test_proxy_sslcerttype(curl):
    curl.setopt(curl.PROXY_SSLCERTTYPE, "PEM")


@util.min_libcurl(7, 52, 0)
@util.only_ssl
def test_proxy_sslkey(curl):
    curl.setopt(curl.PROXY_SSLKEY, "/bogus-sslkey")


@util.min_libcurl(7, 71, 0)
@util.only_ssl_backends("openssl")
def test_proxy_sslkey_blob(curl):
    curl.setopt(curl.PROXY_SSLKEY_BLOB, "bogus-sslkey-blob-as-str")
    curl.setopt(curl.PROXY_SSLKEY_BLOB, None)
    curl.setopt(curl.PROXY_SSLKEY_BLOB, b"bogus-sslkey-blob-as-bytes")
    curl.unsetopt(curl.PROXY_SSLKEY_BLOB)


@util.min_libcurl(7, 52, 0)
@util.only_ssl
def test_proxy_sslkeytype(curl):
    curl.setopt(curl.PROXY_SSLKEYTYPE, "PEM")


@util.min_libcurl(7, 71, 0)
@util.only_ssl_backends("openssl")
def test_proxy_issuercert_blob(curl):
    curl.setopt(curl.PROXY_ISSUERCERT_BLOB, "bogus-issuercert-blob-as-str")
    curl.setopt(curl.PROXY_ISSUERCERT_BLOB, None)
    curl.setopt(curl.PROXY_ISSUERCERT_BLOB, b"bogus-issuercert-blob-as-bytes")
    curl.unsetopt(curl.PROXY_ISSUERCERT_BLOB)


@util.min_libcurl(7, 52, 0)
@util.only_ssl
def test_proxy_keypasswd(curl):
    curl.setopt(curl.PROXY_KEYPASSWD, "secret")


@util.min_libcurl(7, 52, 0)
@util.only_ssl
def test_proxy_ssl_verifypeer(curl):
    curl.setopt(curl.PROXY_SSL_VERIFYPEER, 1)


@util.min_libcurl(7, 52, 0)
@util.only_ssl
def test_proxy_ssl_verifyhost(curl):
    curl.setopt(curl.PROXY_SSL_VERIFYHOST, 2)


@util.min_libcurl(7, 52, 0)
@util.only_ssl
def test_proxy_pinnedpublickey(curl):
    curl.setopt(curl.PROXY_PINNEDPUBLICKEY, "/etc/publickey.der")


@util.min_libcurl(7, 52, 0)
@util.only_ssl
def test_proxy_sslversion_options(curl):
    curl.setopt(curl.PROXY_SSLVERSION, curl.SSLVERSION_DEFAULT)
    curl.setopt(curl.PROXY_SSLVERSION, curl.SSLVERSION_TLSv1)
    curl.setopt(curl.PROXY_SSLVERSION, curl.SSLVERSION_TLSv1_0)
    curl.setopt(curl.PROXY_SSLVERSION, curl.SSLVERSION_TLSv1_1)
    curl.setopt(curl.PROXY_SSLVERSION, curl.SSLVERSION_TLSv1_2)


# SSLVERSION_SSLv* return CURLE_BAD_FUNCTION_ARGUMENT with curl-7.77.0
@util.min_libcurl(7, 52, 0)
@util.removed_in_libcurl(7, 77, 0)
@util.only_ssl
def test_legacy_proxy_sslversion_options(curl):
    curl.setopt(curl.PROXY_SSLVERSION, curl.SSLVERSION_SSLv2)
    curl.setopt(curl.PROXY_SSLVERSION, curl.SSLVERSION_SSLv3)


@util.only_ssl_backends_with_min_libcurl(
    {
        "openssl": (7, 52, 0),
        "wolfssl": (7, 87, 0),
        "schannel": (7, 87, 0),
        "mbedtls": (8, 8, 0),
        "rustls": (8, 10, 0),
    }
)
def test_proxy_ssl_cipher_list(curl):
    curl.setopt(curl.PROXY_SSL_CIPHER_LIST, "RC4-SHA:SHA1+DES")


@util.min_libcurl(7, 52, 0)
@util.only_ssl
def test_proxy_ssl_options(curl):
    curl.setopt(curl.PROXY_SSL_OPTIONS, curl.SSLOPT_ALLOW_BEAST)
    curl.setopt(curl.PROXY_SSL_OPTIONS, curl.SSLOPT_NO_REVOKE)


@util.min_libcurl(7, 52, 0)
@util.only_ssl_backends("openssl", "gnutls")
@util.only_tls_srp
def test_proxy_tlsauth(curl):
    curl.setopt(curl.PROXY_TLSAUTH_USERNAME, "test")
    curl.setopt(curl.PROXY_TLSAUTH_PASSWORD, "test")


@util.min_libcurl(7, 71, 0)
@util.only_ssl_backends("openssl", "gnutls")
def test_proxy_issuercert(curl):
    curl.setopt(curl.PROXY_ISSUERCERT, "/bogus-issuercert")


@util.only_ssl_backends("openssl", "gnutls", "mbedtls", "rustls")
def test_crlfile(curl):
    curl.setopt(curl.CRLFILE, "/bogus-crlfile")


@util.only_ssl
def test_random_file(curl):
    curl.setopt(curl.RANDOM_FILE, "/bogus-random")


@util.only_ssl
def test_egdsocket(curl):
    curl.setopt(curl.EGDSOCKET, "/bogus-egdsocket")


@util.only_ssl_backends_with_min_libcurl(
    {
        "openssl": (7, 9, 0),
        "gnutls": (7, 9, 0),
        "wolfssl": (7, 53, 0),
        "schannel": (7, 61, 0),
        "mbedtls": (8, 8, 0),
        "rustls": (8, 10, 0),
    }
)
def test_ssl_cipher_list(curl):
    if pycurl.COMPILE_SSL_LIB == "gnutls":
        curl.setopt(curl.SSL_CIPHER_LIST, "NORMAL")
    else:
        curl.setopt(curl.SSL_CIPHER_LIST, "RC4-SHA:SHA1+DES")


@util.only_ssl
def test_ssl_sessionid_cache(curl):
    curl.setopt(curl.SSL_SESSIONID_CACHE, True)


@util.removed_in_libcurl(8, 17, 0)
@util.only_gssapi
def test_krblevel(curl):
    curl.setopt(curl.KRBLEVEL, "clear")


@util.removed_in_libcurl(8, 17, 0)
@util.only_gssapi
def test_krb4level(curl):
    curl.setopt(curl.KRB4LEVEL, "clear")


@util.min_libcurl(7, 25, 0)
@util.only_ssl
def test_ssl_options(curl):
    curl.setopt(curl.SSL_OPTIONS, curl.SSLOPT_ALLOW_BEAST)


@util.min_libcurl(7, 44, 0)
@util.only_ssl
def test_ssl_option_no_revoke(curl):
    curl.setopt(curl.SSL_OPTIONS, curl.SSLOPT_NO_REVOKE)


@util.min_libcurl(7, 55, 0)
def test_request_target_option(curl):
    curl.setopt(curl.REQUEST_TARGET, "*")


@util.min_libcurl(7, 64, 0)
def test_http09_allowed_option(curl):
    curl.setopt(curl.HTTP09_ALLOWED, 1)


@util.only_ssl_backends_with_min_libcurl(
    {
        "openssl": (7, 61, 0),
        "wolfssl": (8, 10, 0),
        "mbedtls": (8, 10, 0),
        "rustls": (8, 10, 0),
    }
)
def test_tls13_ciphers(curl):
    curl.setopt(curl.TLS13_CIPHERS, "TLS_CHACHA20_POLY1305_SHA256")


@util.only_ssl_backends_with_min_libcurl(
    {
        "openssl": (7, 61, 0),
        "wolfssl": (8, 10, 0),
        "mbedtls": (8, 10, 0),
        "rustls": (8, 10, 0),
    }
)
def test_proxy_tls13_ciphers(curl):
    curl.setopt(curl.PROXY_TLS13_CIPHERS, "TLS_CHACHA20_POLY1305_SHA256")


@util.min_libcurl(7, 75, 0)
def test_aws_sigv4(curl):
    curl.setopt(curl.AWS_SIGV4, "provider1:provider2")


@util.min_libcurl(8, 2, 0)
def test_haproxy_client_ip(curl):
    curl.setopt(curl.HAPROXY_CLIENT_IP, "192.0.2.22")


@util.min_libcurl(8, 8, 0)
@util.only_ssl_ech
def test_ech(curl):
    curl.setopt(curl.ECH, "true")
    curl.setopt(curl.ECH, "hard")
    curl.setopt(curl.ECH, "false")


def test_append(curl):
    curl.setopt(curl.APPEND, True)


def test_cookiesession(curl):
    curl.setopt(curl.COOKIESESSION, True)


def test_dirlistonly(curl):
    curl.setopt(curl.DIRLISTONLY, True)


@util.only_ssl
def test_keypasswd(curl):
    curl.setopt(curl.KEYPASSWD, "secret")


@util.only_telnet
def test_telnetoptions(curl):
    curl.setopt(curl.TELNETOPTIONS, ("TTYPE=1", "XDISPLOC=2"))


@util.only_ssl
def test_use_ssl(curl):
    curl.setopt(curl.USE_SSL, curl.USESSL_NONE)
    curl.setopt(curl.USE_SSL, curl.USESSL_TRY)
    curl.setopt(curl.USE_SSL, curl.USESSL_CONTROL)
    curl.setopt(curl.USE_SSL, curl.USESSL_ALL)


def test_encoding(curl):
    # old name for ACCEPT_ENCODING
    curl.setopt(curl.ENCODING, "")
    curl.setopt(curl.ENCODING, "application/json")


@util.min_libcurl(7, 21, 6)
def test_accept_encoding(curl):
    curl.setopt(curl.ACCEPT_ENCODING, "")
    curl.setopt(curl.ACCEPT_ENCODING, "application/json")


@util.min_libcurl(7, 21, 6)
def test_transfer_encoding(curl):
    curl.setopt(curl.TRANSFER_ENCODING, True)


@util.min_libcurl(7, 24, 0)
def test_accepttimeout_ms(curl):
    curl.setopt(curl.ACCEPTTIMEOUT_MS, 1000)


@util.min_libcurl(7, 25, 0)
def test_tcp_keepalive(curl):
    curl.setopt(curl.TCP_KEEPALIVE, True)


@util.min_libcurl(7, 25, 0)
def test_tcp_keepidle(curl):
    curl.setopt(curl.TCP_KEEPIDLE, 100)


@util.min_libcurl(7, 25, 0)
def test_tcp_keepintvl(curl):
    curl.setopt(curl.TCP_KEEPINTVL, 100)


@util.min_libcurl(7, 36, 0)
def test_expect_100_timeout_ms(curl):
    curl.setopt(curl.EXPECT_100_TIMEOUT_MS, 100)


@util.min_libcurl(7, 37, 0)
def test_headeropt(curl):
    curl.setopt(curl.HEADEROPT, curl.HEADER_UNIFIED)
    curl.setopt(curl.HEADEROPT, curl.HEADER_SEPARATE)


@util.min_libcurl(7, 42, 0)
def test_path_as_is(curl):
    curl.setopt(curl.PATH_AS_IS, True)


@util.min_libcurl(7, 43, 0)
def test_pipewait(curl):
    curl.setopt(curl.PIPEWAIT, True)


def test_http_version(curl):
    curl.setopt(curl.HTTP_VERSION, curl.CURL_HTTP_VERSION_NONE)
    curl.setopt(curl.HTTP_VERSION, curl.CURL_HTTP_VERSION_1_0)
    curl.setopt(curl.HTTP_VERSION, curl.CURL_HTTP_VERSION_1_1)


@util.min_libcurl(7, 33, 0)
@util.only_http2
def test_http_version_2_0(curl):
    curl.setopt(curl.HTTP_VERSION, curl.CURL_HTTP_VERSION_2_0)


@util.min_libcurl(7, 43, 0)
@util.only_http2
def test_http_version_2(curl):
    curl.setopt(curl.HTTP_VERSION, curl.CURL_HTTP_VERSION_2)


@util.min_libcurl(7, 47, 0)
@util.only_http2
def test_http_version_2tls(curl):
    curl.setopt(curl.HTTP_VERSION, curl.CURL_HTTP_VERSION_2TLS)


@util.min_libcurl(7, 49, 0)
@util.only_http2
def test_http_version_2prior_knowledge(curl):
    curl.setopt(curl.HTTP_VERSION, curl.CURL_HTTP_VERSION_2_PRIOR_KNOWLEDGE)


@util.min_libcurl(7, 66, 0)
@util.only_http3
def test_http_version_3(curl):
    curl.setopt(curl.HTTP_VERSION, curl.CURL_HTTP_VERSION_3)


@util.min_libcurl(7, 88, 0)
@util.only_http3
def test_http_version_3only(curl):
    curl.setopt(curl.HTTP_VERSION, curl.CURL_HTTP_VERSION_3ONLY)


@util.min_libcurl(7, 21, 5)
def test_sockopt_constants(curl):
    assert curl.SOCKOPT_OK is not None
    assert curl.SOCKOPT_ERROR is not None
    assert curl.SOCKOPT_ALREADY_CONNECTED is not None


@util.min_libcurl(7, 40, 0)
def test_proto_smb(curl):
    assert curl.PROTO_SMB is not None
    assert curl.PROTO_SMBS is not None


@util.min_libcurl(7, 21, 4)
@util.only_ssl_backends("openssl", "gnutls")
@util.only_tls_srp
def test_tlsauth(curl):
    curl.setopt(curl.TLSAUTH_TYPE, "SRP")
    curl.setopt(curl.TLSAUTH_USERNAME, "test")
    curl.setopt(curl.TLSAUTH_PASSWORD, "test")


@util.min_libcurl(7, 45, 0)
def test_default_protocol(curl):
    curl.setopt(curl.DEFAULT_PROTOCOL, "http")


@util.min_libcurl(7, 20, 0)
def test_ftp_use_pret(curl):
    curl.setopt(curl.FTP_USE_PRET, True)


@util.min_libcurl(7, 34, 0)
def test_login_options(curl):
    curl.setopt(curl.LOGIN_OPTIONS, "AUTH=NTLM")


@util.min_libcurl(7, 31, 0)
def test_sasl_ir(curl):
    curl.setopt(curl.SASL_IR, True)


@util.min_libcurl(7, 33, 0)
def test_xauth_bearer(curl):
    curl.setopt(curl.XOAUTH2_BEARER, "test")


def test_cookielist_constants():
    assert pycurl.OPT_COOKIELIST == pycurl.COOKIELIST
