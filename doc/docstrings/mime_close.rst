close() -> None

Corresponds to `curl_mime_free`_ in libcurl. This method is automatically
called by pycurl when a ``CurlMime`` object no longer has any references to
it, but can also be called explicitly.

A ``CurlMime`` attached to another one with ``subparts()`` is released by
its parent instead.

A subclass overriding ``__del__`` must call ``super().__del__()``, otherwise
the mime handle is released without running the ``free`` callbacks of its
parts.

``close()`` may not be called while ``perform()`` is running on the ``Curl``
handle the mime belongs to. Doing so raises ``pycurl.error``.

.. _curl_mime_free:
    https://curl.se/libcurl/c/curl_mime_free.html
