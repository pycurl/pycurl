recv_into(buffer[, nbytes]) -> nbytes

Receive data from a connection established with ``CONNECT_ONLY`` into
*buffer*.

*buffer* must be a writable bytes-like object.

If *nbytes* is ``0`` (the default), receive up to ``len(buffer)`` bytes.
Otherwise, receive up to *nbytes* bytes. Returns the number of bytes
received.

Raises ``ValueError`` if *nbytes* is negative or larger than ``len(buffer)``.

Corresponds to `curl_easy_recv`_ in libcurl.

Because the underlying socket is used in non-blocking mode internally,
this method raises ``BlockingIOError`` with ``errno`` set to ``EAGAIN``
when libcurl returns ``CURLE_AGAIN``.

Raises pycurl.error exception upon failures other than ``CURLE_AGAIN``.

.. _curl_easy_recv: https://curl.se/libcurl/c/curl_easy_recv.html
