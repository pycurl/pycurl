notify_enable(*notifications) -> None

Enable one or more libcurl multi notifications. Corresponds to
`curl_multi_notify_enable`_ in libcurl, invoked once per argument.

Each argument must be one of the ``M_NOTIFY_*`` constants
(``pycurl.M_NOTIFY_INFO_READ``, ``pycurl.M_NOTIFY_EASY_DONE``).
Notifications are processed left to right; if libcurl rejects any
of them, ``pycurl.error`` is raised immediately and no rollback of
previously enabled notifications is performed. Calling with no
arguments raises ``TypeError``.

Requires libcurl 8.17.0 or later.

.. _curl_multi_notify_enable:
    https://curl.se/libcurl/c/curl_multi_notify_enable.html
