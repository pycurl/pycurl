Module Functionality
====================

.. module:: pycurl

.. autofunction:: pycurl.global_init

.. autofunction:: pycurl.global_cleanup

**pycurl.version**

This is a string with version information on libcurl, corresponding to
`curl_version`_ in libcurl.

Example usage:

::

    >>> import pycurl
    >>> pycurl.version
    'PycURL/7.19.3 libcurl/7.33.0 OpenSSL/0.9.8x zlib/1.2.7'

.. autofunction:: pycurl.version_info

Example usage:

::

    >>> import pycurl
    >>> pycurl.version_info()
    (3, '7.33.0', 467200, 'amd64-portbld-freebsd9.1', 33436, 'OpenSSL/0.9.8x',
    0, '1.2.7', ('dict', 'file', 'ftp', 'ftps', 'gopher', 'http', 'https',
    'imap', 'imaps', 'pop3', 'pop3s', 'rtsp', 'smtp', 'smtps', 'telnet',
    'tftp'), None, 0, None)

.. autoclass:: pycurl.Curl

.. autoclass:: pycurl.CurlMulti

.. autoclass:: pycurl.CurlShare


.. _curl_version: http://curl.haxx.se/libcurl/c/curl_version.html
