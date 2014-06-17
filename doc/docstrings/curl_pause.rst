pause(bitmask) -> None

Pause or unpause a curl handle. Bitmask should be a value such as
PAUSE_RECV or PAUSE_CONT.

Corresponds to `curl_easy_pause`_ in libcurl. The argument should be
derived from the ``PAUSE_RECV``, ``PAUSE_SEND``, ``PAUSE_ALL`` and
``PAUSE_CONT`` constants.

Raises pycurl.error exception upon failure.

.. _curl_easy_pause: http://curl.haxx.se/libcurl/c/curl_easy_pause.html
