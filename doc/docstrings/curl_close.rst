close() -> None

Close handle and end curl session.

Corresponds to `curl_easy_cleanup`_ in libcurl. This method is
automatically called by pycurl when a Curl object no longer has any
references to it, but can also be called explicitly.

.. _curl_easy_cleanup:
    http://curl.haxx.se/libcurl/c/curl_easy_cleanup.html
