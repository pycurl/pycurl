pycurl Module Functionality
===========================

.. module:: pycurl

.. autofunction:: pycurl.global_init

.. autofunction:: pycurl.global_cleanup

.. data:: version

    This is a string with version information on libcurl, corresponding to
    `curl_version`_ in libcurl.

    Example usage:

    ::

        >>> import pycurl
        >>> pycurl.version
        'PycURL/7.19.3 libcurl/7.33.0 OpenSSL/0.9.8x zlib/1.2.7'

.. autofunction:: pycurl.version_info

.. autoclass:: pycurl.Curl
    :noindex:

.. autoclass:: pycurl.CurlMulti
    :noindex:

.. autoclass:: pycurl.CurlShare
    :noindex:

.. _curl_version: http://curl.haxx.se/libcurl/c/curl_version.html
