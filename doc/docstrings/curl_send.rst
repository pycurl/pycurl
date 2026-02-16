send(bytes) -> count

Send data over a connection established with ``CONNECT_ONLY``.

*data* may be any bytes-like object.

Returns the number of bytes sent. If fewer than ``len(data)`` bytes are sent,
the remaining data should be sent in a subsequent call.

Corresponds to `curl_easy_send`_ in libcurl.

Because the underlying socket is used in non-blocking mode internally,
this method raises ``BlockingIOError`` with ``errno`` set to ``EAGAIN``
when libcurl returns ``CURLE_AGAIN``.

Raises pycurl.error exception upon failures other than ``CURLE_AGAIN``.

.. _curl_easy_send: https://curl.se/libcurl/c/curl_easy_send.html
