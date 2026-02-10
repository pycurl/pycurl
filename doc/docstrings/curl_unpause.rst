unpause() -> None

Unpause a curl handle.

Equivalent to ``pause(PAUSE_CONT)``.

Corresponds to `curl_easy_pause`_ in libcurl.

Raises pycurl.error exception upon failure.

.. _curl_easy_pause: https://curl.haxx.se/libcurl/c/curl_easy_pause.html
