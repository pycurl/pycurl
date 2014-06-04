setopt(option, value) -> None

Set curl session option.

Corresponds to `curl_easy_setopt`_ in libcurl, where *option* is
specified with the ``CURLOPT_*`` constants in libcurl, except that
the ``CURLOPT_`` prefix has been removed. (See below for exceptions.)
The type for *value* depends on the option, and can be either
a string, integer, long integer, file object, list, or function.

In order to distinguish between similarly-named CURLOPT and CURLINFO
constants, some have ``OPT_`` and ``INFO_`` prefixes. These are
``INFO_FILETIME``, ``OPT_FILETIME``, ``INFO_COOKIELIST`` (but ``setopt`` uses
``COOKIELIST``!), ``INFO_CERTINFO``, and ``OPT_CERTINFO``.

Example usage::

    import pycurl
    c = pycurl.Curl()
    c.setopt(pycurl.URL, "http://www.python.org/")
    c.setopt(pycurl.HTTPHEADER, ["Accept:"])
    import StringIO
    b = StringIO.StringIO()
    c.setopt(pycurl.WRITEFUNCTION, b.write)
    c.setopt(pycurl.FOLLOWLOCATION, 1)
    c.setopt(pycurl.MAXREDIRS, 5)
    c.perform()
    print b.getvalue()
    ...

Raises pycurl.error exception upon failure.

.. _curl_easy_setopt: http://curl.haxx.se/libcurl/c/curl_easy_setopt.html
