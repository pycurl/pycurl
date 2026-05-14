url_strerror(errornum) -> str

Return a string describing a libcurl URL-API error code.

*errornum* is a ``CURLUcode`` as returned by ``curl_url_*`` functions.

Requires libcurl 7.80.0 or later; not exposed on older builds.

Corresponds to `curl_url_strerror`_ in libcurl.

.. _curl_url_strerror: https://curl.haxx.se/libcurl/c/curl_url_strerror.html
