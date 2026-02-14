recv(buffersize) -> data

Receive data from a connection established with ``CONNECT_ONLY``.

Receive up to *buffersize* bytes and return them as a ``bytes`` object.
A returned empty ``bytes`` object indicates that the peer has closed the
connection.

Raises ``ValueError`` if *buffersize* is negative.

Corresponds to `curl_easy_recv`_ in libcurl.

Because the underlying socket is used in non-blocking mode internally,
this method raises ``BlockingIOError`` with ``errno`` set to ``EAGAIN``
when libcurl returns ``CURLE_AGAIN``.

Raises pycurl.error exception upon failures other than ``CURLE_AGAIN``.

.. _curl_easy_recv: https://curl.se/libcurl/c/curl_easy_recv.html
