close() -> None

Corresponds to `curl_multi_cleanup`_ in libcurl. This method is
automatically called by pycurl when a ``CurlMulti`` object no longer has
any references to it, but can also be called explicitly.

It removes all easy handles from the multi handle before closing the
multi handle.

If the ``CurlMulti`` was constructed with ``close_handles=True``, the
removed easy handles are also closed after removal. Otherwise, they
remain open.

``close()`` may not be called while ``perform()`` or ``socket_action()``
is on the stack (for example, from inside ``M_SOCKETFUNCTION`` or
``M_TIMERFUNCTION``); doing so raises ``pycurl.error``.

.. _curl_multi_cleanup:
    https://curl.haxx.se/libcurl/c/curl_multi_cleanup.html
