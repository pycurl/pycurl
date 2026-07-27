getpart(part, flags=0) -> str or None

Return one URL component, or ``None`` when it is absent.

*part* is one of the ``UPART_*`` constants. *flags* is a combination of the
``U_*`` constants, for example ``U_URLDECODE``. Errors other than an absent
part raise ``pycurl.error``.

Corresponds to `curl_url_get`_ in libcurl.

.. _curl_url_get: https://curl.se/libcurl/c/curl_url_get.html
