Troubleshooting
===============

The first step of troubleshooting issues in programs using PycURL is
identifying which piece of software is responsible for the misbehavior.
PycURL is a thin wrapper around libcurl; libcurl performs most of the
network operations and transfer-related issues are generally the domain
of libcurl.

If your issue is transfer-related (timeout, connection failure, transfer
failure, ``perform`` hangs, etc.) the first step in troubleshooting is
setting the ``VERBOSE`` flag for the operation. libcurl will then output
debugging information as the transfer executes::

    >>> import pycurl
    >>> curl = pycurl.Curl()
    >>> curl.setopt(curl.VERBOSE, True)
    >>> curl.setopt(curl.URL, 'https://www.python.org')
    >>> curl.setopt(curl.WRITEDATA, open('/dev/null', 'w'))
    >>> curl.perform()
    * Hostname www.python.org was found in DNS cache
    *   Trying 151.101.208.223...
    * TCP_NODELAY set
    * Connected to www.python.org (151.101.208.223) port 443 (#1)
    * found 173 certificates in /etc/ssl/certs/ca-certificates.crt
    * found 696 certificates in /etc/ssl/certs
    * ALPN, offering http/1.1
    * SSL re-using session ID
    * SSL connection using TLS1.2 / ECDHE_RSA_AES_128_GCM_SHA256
    *      server certificate verification OK
    *      server certificate status verification SKIPPED
    *      common name: www.python.org (matched)
    *      server certificate expiration date OK
    *      server certificate activation date OK
    *      certificate public key: RSA
    *      certificate version: #3
    *      subject: 
    *      start date: Sat, 17 Jun 2017 00:00:00 GMT
    *      expire date: Thu, 27 Sep 2018 12:00:00 GMT
    *      issuer: C=US,O=DigiCert Inc,OU=www.digicert.com,CN=DigiCert SHA2 Extended Validation Server CA
    *      compression: NULL
    * ALPN, server accepted to use http/1.1
    > GET / HTTP/1.1
    Host: www.python.org
    User-Agent: PycURL/7.43.0.1 libcurl/7.52.1 GnuTLS/3.5.8 zlib/1.2.8 libidn2/0.16 libpsl/0.17.0 (+libidn2/0.16) libssh2/1.7.0 nghttp2/1.18.1 librtmp/2.3
    Accept: */*

    < HTTP/1.1 200 OK
    < Server: nginx
    < Content-Type: text/html; charset=utf-8
    < X-Frame-Options: SAMEORIGIN
    < x-xss-protection: 1; mode=block
    < X-Clacks-Overhead: GNU Terry Pratchett
    < Via: 1.1 varnish
    < Fastly-Debug-Digest: a63ab819df3b185a89db37a59e39f0dd85cf8ee71f54bbb42fae41670ae56fd2
    < Content-Length: 48893
    < Accept-Ranges: bytes
    < Date: Thu, 07 Dec 2017 07:28:32 GMT
    < Via: 1.1 varnish
    < Age: 2497
    < Connection: keep-alive
    < X-Served-By: cache-iad2146-IAD, cache-ewr18146-EWR
    < X-Cache: HIT, HIT
    < X-Cache-Hits: 2, 2
    < X-Timer: S1512631712.274059,VS0,VE0
    < Vary: Cookie
    < Strict-Transport-Security: max-age=63072000; includeSubDomains
    < 
    * Curl_http_done: called premature == 0
    * Connection #1 to host www.python.org left intact
    >>> 

The verbose output in the above example includes:

- DNS resolution
- SSL connection
- SSL certificate verification
- Headers sent to the server
- Headers received from the server

If the verbose output indicates something you believe is incorrect,
the next step is to perform an identical transfer using ``curl`` command-line
utility and verify that the behavior is PycURL-specific, as in most cases
it is not. This is also a good time to check the behavior of the latest
version of libcurl.
