global_init(option) -> None

Initialize curl environment.

*option* is one of the constants pycurl.GLOBAL_SSL, pycurl.GLOBAL_WIN32,
pycurl.GLOBAL_ALL, pycurl.GLOBAL_NOTHING, pycurl.GLOBAL_DEFAULT.

Corresponds to `curl_global_init`_ in libcurl.

.. _curl_global_init: http://curl.haxx.se/libcurl/c/curl_global_init.html
