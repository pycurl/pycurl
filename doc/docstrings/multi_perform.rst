perform() -> tuple of status and the number of active Curl objects

Corresponds to `curl_multi_perform`_ in libcurl.

This method raises an exception if ``curl_multi_perform`` returns a value other than
``CURLM_OK``.

.. _curl_multi_perform:
    https://curl.haxx.se/libcurl/c/curl_multi_perform.html
