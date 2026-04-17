.. _curlobject:

Curl Object
===========

.. autoclass:: pycurl.Curl

    Curl objects have the following methods:

    .. automethod:: pycurl.Curl.close

    .. _setopt:
    .. automethod:: pycurl.Curl.setopt

    .. _perform:
    .. automethod:: pycurl.Curl.perform

    .. _perform_rb:
    .. automethod:: pycurl.Curl.perform_rb

    .. _perform_rs:
    .. automethod:: pycurl.Curl.perform_rs

    .. _getinfo:
    .. automethod:: pycurl.Curl.getinfo

    .. _getinfo_raw:
    .. automethod:: pycurl.Curl.getinfo_raw

    .. automethod:: pycurl.Curl.reset

    .. _unsetopt:
    .. automethod:: pycurl.Curl.unsetopt

    .. automethod:: pycurl.Curl.pause

    .. _recv:
    .. automethod:: pycurl.Curl.recv

    .. _recv_into:
    .. automethod:: pycurl.Curl.recv_into

    .. _send:
    .. automethod:: pycurl.Curl.send

    .. _errstr:
    .. automethod:: pycurl.Curl.errstr

    .. _errstr_raw:
    .. automethod:: pycurl.Curl.errstr_raw

    .. automethod:: pycurl.Curl.setopt_string

    WebSocket methods (libcurl 7.86.0 or later):

    .. _ws_send:
    .. automethod:: pycurl.Curl.ws_send

    .. _ws_recv:
    .. automethod:: pycurl.Curl.ws_recv

    .. _ws_recv_into:
    .. automethod:: pycurl.Curl.ws_recv_into

    .. _ws_meta:
    .. automethod:: pycurl.Curl.ws_meta

    .. _ws_close:
    .. automethod:: pycurl.Curl.ws_close

    PycURL supports libcurl's two documented WebSocket usage models:

    - **Detached mode.** Set ``CONNECT_ONLY`` to ``2``, call
      :py:meth:`perform` to drive the handshake, and then drive the
      connection yourself with :py:meth:`ws_send` and :py:meth:`ws_recv`
      (or :py:meth:`ws_recv_into`). In this mode, frame metadata is
      returned as the second element of each receive call's result.
    - **Callback-receive mode.** Set a ``WRITEFUNCTION`` callback, leave
      ``CONNECT_ONLY`` unset (or ``0``), and call :py:meth:`perform`.
      libcurl drives the transfer and delivers each received frame
      chunk to the write callback. Call :py:meth:`ws_meta` from inside
      the callback to retrieve the current chunk's ``WsFrame`` metadata;
      ``ws_meta()`` returns ``None`` outside that context.

    PycURL does not reassemble fragmented messages or manage the
    WebSocket close handshake. libcurl automatically replies to ping
    frames unless ``WS_NOAUTOPONG`` or ``WS_RAW_MODE`` is enabled.

    Frame metadata is exposed through the module-level ``WsFrame``
    namedtuple (``age``, ``flags``, ``offset``, ``bytesleft``, ``len``).
    The ``flags`` field is a bitmask of the ``WS_*`` constants.

    **Caveats and sharp edges:**

    - **Do not combine ``CONNECT_ONLY=2`` with ``FORBID_REUSE``** —
      libcurl tears down the connection after the handshake
      ``perform()`` returns and the first ``ws_send()`` fails with
      ``CURLE_UNSUPPORTED_PROTOCOL``.
    - **A WebSocket handle is not thread-safe** — see
      :ref:`thread-safety`.
    - **``WS_RAW_MODE`` (via ``CURLOPT_WS_OPTIONS``) changes framing
      semantics.** libcurl ignores ``ws_send``'s ``flags`` argument and
      writes bytes verbatim. Raw-mode callers should pass bytes-like
      data; Python-side ``str``/bytes inference still runs but the
      flag bits never reach the wire.
    - **Replying inside a ``WRITEFUNCTION`` is allowed** — see
      :ref:`callbacks`. ``ws_send``/``ws_close`` behave as blocking
      sends in that context; ``ws_recv`` / ``ws_recv_into`` remain
      detached-only.
    - **Runtime probe**: ``'ws' in pycurl.version_info()[8]``.
      Compile-time: ``hasattr(pycurl, 'WS_TEXT')``.
