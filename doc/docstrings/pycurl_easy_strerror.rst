easy_strerror(errornum) -> str

Return a string describing a libcurl easy-interface error code.

*errornum* is a ``CURLcode``, usually exposed by PycURL as a
``pycurl.E_*`` constant.

Corresponds to `curl_easy_strerror`_ in libcurl.

.. _curl_easy_strerror: https://curl.haxx.se/libcurl/c/curl_easy_strerror.html
