encoder(encoding) -> None

Set the content transfer encoding for this part.

Corresponds to `curl_mime_encoder`_ in libcurl.

:param str encoding: the encoding, for example ``"base64"``. A byte string
    is also accepted.

.. _curl_mime_encoder:
    https://curl.se/libcurl/c/curl_mime_encoder.html
