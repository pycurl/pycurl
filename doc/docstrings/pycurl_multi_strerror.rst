multi_strerror(errornum) -> str

Return a string describing a libcurl multi-interface error code.

*errornum* is a ``CURLMcode``, usually exposed by PycURL as a
``pycurl.E_MULTI_*`` constant.

Corresponds to `curl_multi_strerror`_ in libcurl.

.. _curl_multi_strerror: https://curl.haxx.se/libcurl/c/curl_multi_strerror.html
