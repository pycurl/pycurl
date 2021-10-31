duphandle() -> Curl

Clone a curl handle. This function will return a new curl handle,
a duplicate, using all the options previously set in the input curl handle.
Both handles can subsequently be used independently.

The new handle will not inherit any state information, no connections,
no SSL sessions and no cookies. It also will not inherit any share object
states or options (it will be made as if SHARE was unset).

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
