pause(bitmask=PAUSE_ALL) -> None

Pause or unpause a curl handle. ``bitmask`` defaults to ``PAUSE_ALL``.
Pass a value such as ``PAUSE_RECV``, ``PAUSE_SEND``, or ``PAUSE_CONT`` to
override.

Corresponds to `curl_easy_pause`_ in libcurl. The argument should be
derived from the ``PAUSE_RECV``, ``PAUSE_SEND``, ``PAUSE_ALL`` and
``PAUSE_CONT`` constants.

``pause()`` may be called from inside one of this handle's callbacks
or from the thread running the transfer. Calls from other threads while
``perform()`` is running are rejected with ``pycurl.error``, as libcurl
does not support them.

Raises pycurl.error exception upon failure.

.. _curl_easy_pause: https://curl.haxx.se/libcurl/c/curl_easy_pause.html
