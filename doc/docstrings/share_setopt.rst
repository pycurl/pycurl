setopt(option, value) -> None

Set curl share option.

Corresponds to `curl_share_setopt`_ in libcurl, where *option* is
specified with the ``CURLSHOPT_*`` constants in libcurl, except that the
``CURLSHOPT_`` prefix has been changed to ``SH_``. Currently, *value* must be
either ``LOCK_DATA_COOKIE`` or ``LOCK_DATA_DNS``.

Example usage::

    import pycurl
    curl = pycurl.Curl()
    s = pycurl.CurlShare()
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_COOKIE)
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_DNS)
    curl.setopt(pycurl.URL, 'http://curl.haxx.se')
    curl.setopt(pycurl.SHARE, s)
    curl.perform()
    curl.close()

Raises pycurl.error exception upon failure.

.. _curl_share_setopt:
    http://curl.haxx.se/libcurl/c/curl_share_setopt.html
