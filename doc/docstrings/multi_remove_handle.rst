remove_handle(Curl object) -> None

Corresponds to `curl_multi_remove_handle`_ in libcurl. This method
removes an existing and valid Curl object from the CurlMulti object.

IMPORTANT NOTE: remove_handle does not implicitly remove a Python reference
from the Curl object (and thus does not decrease the reference count on the
Curl object).

.. _curl_multi_remove_handle:
    http://curl.haxx.se/libcurl/c/curl_multi_remove_handle.html
