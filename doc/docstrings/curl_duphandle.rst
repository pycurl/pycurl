duphandle() -> Curl

Clone a curl handle. This function will return a new curl handle,
a duplicate, using all the options previously set in the input curl handle.
Both handles can subsequently be used independently.

The new handle will not inherit any state information, no connections,
no SSL sessions and no cookies. It also will not inherit any share object
states or options (it will be made as if SHARE was unset).

When ``MIMEPOST`` includes parts configured with ``CurlMimePart.data_cb()``,
libcurl duplicates callback userdata pointers into the duplicated handle.
Design callback state (especially any ``free`` hook side effects) so that
multiple handle instances can release it safely.
See also `curl_mime_data_cb`_ in libcurl.

Corresponds to `curl_easy_duphandle`_ in libcurl.

Example usage::

    import pycurl
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, "https://python.org")
    dup = curl.duphandle()
    curl.perform()
    dup.perform()

.. _curl_easy_duphandle:
    https://curl.se/libcurl/c/curl_easy_duphandle.html

.. _curl_mime_data_cb:
    https://curl.se/libcurl/c/curl_mime_data_cb.html
