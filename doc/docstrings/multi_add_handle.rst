add_handle(Curl object) -> None

Corresponds to `curl_multi_add_handle`_ in libcurl. This method adds an
existing and valid Curl object to the CurlMulti object.

*Changed in version 7.43.0.2:* add_handle now ensures that the Curl object
is not garbage collected while it is being used by a CurlMulti object.
Previously application had to maintain an outstanding reference to the Curl
object to keep it from being garbage collected.

.. _curl_multi_add_handle:
    https://curl.haxx.se/libcurl/c/curl_multi_add_handle.html
