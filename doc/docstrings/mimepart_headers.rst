headers(headers) -> None

Set custom headers for this part, as a list or tuple of strings.

Corresponds to `curl_mime_headers`_ in libcurl.

:param headers: the headers, as a list or tuple of strings, or ``None`` to
    clear them.

.. _curl_mime_headers:
    https://curl.se/libcurl/c/curl_mime_headers.html
