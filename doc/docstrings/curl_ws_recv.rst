ws_recv(buffersize) -> (data, meta)

Receive a WebSocket frame chunk on a connection established with
``CONNECT_ONLY=2``.

Receive up to *buffersize* bytes. Returns a 2-tuple ``(data, meta)``
where *data* is a ``bytes`` object containing the received payload chunk
and *meta* is a ``WsFrame`` namedtuple carrying the per-frame metadata
returned by libcurl for this call (``age``, ``flags``, ``offset``,
``bytesleft``, ``len``).

A single call may return only part of a frame's payload: check
``meta.bytesleft`` to decide whether to loop. Reassembly of fragmented
messages is the caller's responsibility.

A *buffersize* of ``0`` performs a zero-length ``curl_ws_recv`` call.
This returns ``(b"", meta)`` so callers can inspect frame metadata
without consuming payload bytes. Frames with empty payload are consumed
by this action.

Raises ``ValueError`` if *buffersize* is negative.

Corresponds to `curl_ws_recv`_ in libcurl. Requires libcurl 7.86.0 or
later.

Because the underlying socket is used in non-blocking mode internally,
this method raises ``BlockingIOError`` with ``errno`` set to ``EAGAIN``
when libcurl returns ``CURLE_AGAIN``.

Raises pycurl.error exception upon failures other than ``CURLE_AGAIN``.

.. _curl_ws_recv: https://curl.se/libcurl/c/curl_ws_recv.html
