setpart(part, value, flags=0) -> None

Set one URL component.

*part* is one of the ``UPART_*`` constants. *value* is a string or bytes, or
``None`` to remove the part. *flags* is a combination of the ``U_*`` constants,
for example ``U_URLENCODE`` or ``U_APPENDQUERY``. On failure ``pycurl.error``
is raised.

Corresponds to `curl_url_set`_ in libcurl.

.. _curl_url_set: https://curl.se/libcurl/c/curl_url_set.html
