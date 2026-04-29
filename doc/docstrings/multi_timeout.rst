timeout() -> int

Returns how long to wait for action before proceeding, in milliseconds, or
``-1`` if libcurl has no timeout currently set.
Corresponds to `curl_multi_timeout`_ in libcurl.

.. _curl_multi_timeout: https://curl.haxx.se/libcurl/c/curl_multi_timeout.html
