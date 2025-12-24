close() -> None

Corresponds to `curl_multi_cleanup`_ in libcurl. This method is
automatically called by pycurl when a ``CurlMulti`` object no longer has
any references to it, but can also be called explicitly.

It removes all easy handles from the multi handle before closing the
multi handle.

If ``closed_handles`` is ``True``, the removed easy handles are closed
after removal. Otherwise, they remain open.

.. _curl_multi_cleanup:
    https://curl.haxx.se/libcurl/c/curl_multi_cleanup.html
