add_handle(Curl object) -> None

Corresponds to `curl_multi_add_handle`_ in libcurl. This method adds an
existing and valid Curl object to the CurlMulti object.

IMPORTANT NOTE: add_handle does not implicitly add a Python reference to the
Curl object (and thus does not increase the reference count on the Curl
object).

.. _curl_multi_add_handle:
    http://curl.haxx.se/libcurl/c/curl_multi_add_handle.html
