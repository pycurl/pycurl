subparts(child) -> None

Attach another ``CurlMime`` as the multipart content of this part.

Ownership of *child* transfers to this tree, so it is released with the
parent.

Corresponds to `curl_mime_subparts`_ in libcurl.

:param CurlMime child: the tree to attach. It must use the same ``Curl``
    handle, must not already be attached, and must not be set as ``MIMEPOST``.

.. _curl_mime_subparts:
    https://curl.se/libcurl/c/curl_mime_subparts.html
