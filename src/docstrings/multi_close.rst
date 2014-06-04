close() -> None

Corresponds to `curl_multi_cleanup`_ in libcurl. This method is
automatically called by pycurl when a CurlMulti object no longer has any
references to it, but can also be called explicitly.

.. _curl_multi_cleanup:
    http://curl.haxx.se/libcurl/c/curl_multi_cleanup.html
