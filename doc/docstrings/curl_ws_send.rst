ws_send(data, flags=None, fragsize=0, encoding='utf-8') -> count

Send a WebSocket frame. In detached mode this requires ``CONNECT_ONLY=2``;
inside an active ``WRITEFUNCTION`` callback it may also be used to send
a blocking reply.

*data* may be a ``str`` or any bytes-like object. ``str`` is encoded
with *encoding* (UTF-8 by default); characters that are not
representable in *encoding* raise ``UnicodeEncodeError``. Passing
``None`` raises ``TypeError`` — use ``b""`` for an empty payload.

*flags* is a bitmask built from the frame-type constants ``WS_TEXT``,
``WS_BINARY``, ``WS_CONT``, ``WS_CLOSE``, ``WS_PING``, ``WS_PONG``. When
``flags`` is omitted (``None``), the frame type is inferred: ``str`` ->
``WS_TEXT``, bytes-like -> ``WS_BINARY``. Explicit flags win. ``str`` +
``WS_BINARY`` and ``str`` + ``WS_CLOSE`` raise ``TypeError`` (use
:py:meth:`ws_close` for close frames, or pass bytes-like data).

*fragsize* maps to ``curl_ws_send``'s ``fragsize`` parameter; ``0``
means "whole message". ``WS_OFFSET`` is the companion flag for
multi-call fragmented sends; see the libcurl docs for the rules.

Returns the number of bytes accepted by libcurl.

Raises ``BlockingIOError`` (``errno=EAGAIN``) in detached mode when
libcurl returns ``CURLE_AGAIN``. Inside a ``WRITEFUNCTION`` callback
libcurl treats the call as blocking and returns only once the frame has
been fully sent; ``BlockingIOError`` does not apply. Calls from other
threads while ``perform()`` is running are rejected.

Corresponds to `curl_ws_send`_ in libcurl. Requires libcurl 7.86.0 or
later. Raises ``pycurl.error`` for libcurl failures other than
``CURLE_AGAIN``.

.. _curl_ws_send: https://curl.se/libcurl/c/curl_ws_send.html
