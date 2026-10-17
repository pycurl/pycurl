CurlMime(curl) -> New CurlMime object

Creates a new :ref:`mime` tree bound to *curl*, corresponding to a
``curl_mime`` handle in libcurl. Pass it to
``Curl.setopt(pycurl.MIMEPOST, mime)`` to send it as the request body.

The ``CurlMime`` object can be used as a context manager. Exiting the
context calls ``close()``.

Corresponds to `curl_mime_init`_ in libcurl.

:param Curl curl: the :ref:`Curl object <curlobject>` this tree belongs to.
    The handle must be open and not performing.

.. _curl_mime_init:
    https://curl.se/libcurl/c/curl_mime_init.html
