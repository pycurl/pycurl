setopt(option, value) -> None

Set curl share option.

Corresponds to `curl_share_setopt`_ in libcurl, where *option* is
specified with the ``CURLSHOPT_*`` constants in libcurl, except that the
``CURLSHOPT_`` prefix has been changed to ``SH_``. Currently, *value* must be
one of: ``LOCK_DATA_COOKIE``, ``LOCK_DATA_DNS``, ``LOCK_DATA_SSL_SESSION`` or
``LOCK_DATA_CONNECT``.

Example usage::

    import pycurl
    curl = pycurl.Curl()
    s = pycurl.CurlShare()
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_COOKIE)
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_DNS)
    curl.setopt(pycurl.URL, 'https://curl.haxx.se')
    curl.setopt(pycurl.SHARE, s)
    curl.perform()
    curl.close()

Raises pycurl.error exception upon failure.

.. _curl_share_setopt:
    https://curl.haxx.se/libcurl/c/curl_share_setopt.html
