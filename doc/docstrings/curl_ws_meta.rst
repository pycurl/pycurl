ws_meta() -> WsFrame or None

Return a snapshot of the current WebSocket frame's metadata.

This is a callback-context helper. It is intended to be called from
inside an active ``WRITEFUNCTION`` callback on a WebSocket transfer,
where it returns a ``WsFrame`` namedtuple with the metadata of the
chunk currently being delivered.

Outside that context — including when used in detached mode
(``CONNECT_ONLY=2``), after ``perform()`` has returned, or on a
non-WebSocket transfer — libcurl's ``curl_ws_meta()`` returns ``NULL``
and PycURL maps that ``NULL`` to Python ``None``. No exception is
raised; callers can use ``if c.ws_meta() is None`` to probe context
validity.

In detached mode, prefer the metadata returned directly by
``ws_recv()`` / ``ws_recv_into()`` rather than a separate ``ws_meta()``
call.

Corresponds to `curl_ws_meta`_ in libcurl. Requires libcurl 7.86.0 or
later.

.. _curl_ws_meta: https://curl.se/libcurl/c/curl_ws_meta.html
