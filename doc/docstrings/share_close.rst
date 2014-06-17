close() -> None

Close shared handle.

Corresponds to `curl_share_cleanup`_ in libcurl. This method is
automatically called by pycurl when a CurlShare object no longer has
any references to it, but can also be called explicitly.

.. _curl_share_cleanup:
    http://curl.haxx.se/libcurl/c/curl_share_cleanup.html
