reset() -> None

Reset all options set on curl handle to default values, but preserves
live connections, session ID cache, DNS cache, cookies, and shares.

Corresponds to `curl_easy_reset`_ in libcurl.

.. _curl_easy_reset: http://curl.haxx.se/libcurl/c/curl_easy_reset.html
