ws_close(code=None, reason=None, encoding='utf-8') -> count

Send a WebSocket close frame. In detached mode this requires
``CONNECT_ONLY=2``; inside an active ``WRITEFUNCTION`` callback it may
also be used to send a blocking reply.

Builds an RFC 6455 §5.5.1 close payload — an optional 2-byte big-endian
status *code* followed by an optional UTF-8 *reason* — and sends it as
a ``WS_CLOSE`` control frame. Prefer this over
``ws_send(bytes, WS_CLOSE)``: the payload format is non-obvious.

*code* is the WebSocket close status code. Omitted (``None``) sends an
empty close payload. When specified, must be a valid wire code per RFC
6455 §7.4.1: ``1000`` (normal), ``1001`` (going away), ``1002``, ``1003``,
``1007``-``1014``, or a private-use value in ``3000..4999``. Codes
``1004``, ``1005``, ``1006``, ``1015`` are RFC-forbidden to send and
rejected.

*reason* may be a ``str`` or any bytes-like object. ``str`` is encoded
with *encoding* (UTF-8 by default). The resulting bytes must be valid
UTF-8 on the wire; invalid UTF-8 raises ``UnicodeDecodeError``,
non-encodable input raises ``UnicodeEncodeError``. ``reason`` without
``code`` raises ``ValueError``. The combined payload (2-byte code +
reason) must not exceed 125 bytes (RFC 6455 §5.5).

Returns the number of bytes accepted by libcurl.

Same blocking / non-blocking semantics as :py:meth:`ws_send`. Calls
from other threads while ``perform()`` is running are rejected.

Corresponds to `curl_ws_send`_ with ``CURLWS_CLOSE``. Requires libcurl
7.86.0 or later. Raises ``pycurl.error`` for libcurl failures other
than ``CURLE_AGAIN``.

.. _curl_ws_send: https://curl.se/libcurl/c/curl_ws_send.html
