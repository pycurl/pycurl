data(data) -> None

Set in-memory data for this part.

*data* may be a byte string, an ASCII string, or any object supporting the
buffer protocol. The data is copied, so the object does not need to outlive
the call.

Corresponds to `curl_mime_data`_ in libcurl.

:param data: the content, as ``bytes``, an ASCII ``str``, or any object
    supporting the buffer protocol.

.. _curl_mime_data:
    https://curl.se/libcurl/c/curl_mime_data.html
