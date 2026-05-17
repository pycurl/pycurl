notify_disable(*notifications) -> None

Disable one or more libcurl multi notifications. Corresponds to
`curl_multi_notify_disable`_ in libcurl, invoked once per argument.
Mirrors :py:meth:`notify_enable <pycurl.CurlMulti.notify_enable>` —
same argument shape, same left-to-right, first-error-no-rollback
semantics, and same ``TypeError`` on zero arguments.

Requires libcurl 8.17.0 or later.

.. _curl_multi_notify_disable:
    https://curl.se/libcurl/c/curl_multi_notify_disable.html
