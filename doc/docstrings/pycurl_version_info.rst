version_info() -> tuple

Returns a 12-tuple with the version info.

Corresponds to `curl_version_info`_ in libcurl. Returns a tuple of
information which is similar to the ``curl_version_info_data`` struct
returned by ``curl_version_info()`` in libcurl.

Example usage::

    >>> import pycurl
    >>> pycurl.version_info()
    (3, '7.33.0', 467200, 'amd64-portbld-freebsd9.1', 33436, 'OpenSSL/0.9.8x',
    0, '1.2.7', ('dict', 'file', 'ftp', 'ftps', 'gopher', 'http', 'https',
    'imap', 'imaps', 'pop3', 'pop3s', 'rtsp', 'smtp', 'smtps', 'telnet',
    'tftp'), None, 0, None)

.. _curl_version_info: http://curl.haxx.se/libcurl/c/curl_version_info.html
