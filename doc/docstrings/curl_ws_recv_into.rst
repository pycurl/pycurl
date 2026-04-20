ws_recv_into(buffer[, nbytes]) -> (nbytes, meta)

Receive a WebSocket frame chunk on a connection established with
``CONNECT_ONLY=2`` into a caller-owned writable *buffer*.

*buffer* must be a writable bytes-like object (e.g. ``bytearray``,
``memoryview``, ``array.array``).

If *nbytes* is ``0`` (the default), receive up to ``len(buffer)`` bytes.
Otherwise, receive up to *nbytes* bytes.

Returns a 2-tuple ``(nbytes, meta)`` where *nbytes* is the number of
bytes written into *buffer* and *meta* is a ``WsFrame`` namedtuple with
the per-frame metadata returned by libcurl for this call.

Raises ``ValueError`` if *nbytes* is negative or larger than
``len(buffer)``.

If *buffer* has length ``0``, this performs a zero-length
``curl_ws_recv`` call and returns ``(0, meta)`` so callers can inspect
frame metadata without consuming payload bytes. Frames with empty
payload are consumed by this action.

Corresponds to `curl_ws_recv`_ in libcurl. Requires libcurl 7.86.0 or
later.

Because the underlying socket is used in non-blocking mode internally,
this method raises ``BlockingIOError`` with ``errno`` set to ``EAGAIN``
when libcurl returns ``CURLE_AGAIN``.

Raises pycurl.error exception upon failures other than ``CURLE_AGAIN``.

.. _curl_ws_recv: https://curl.se/libcurl/c/curl_ws_recv.html
