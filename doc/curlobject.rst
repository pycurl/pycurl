Curl Object
===========

Curl objects have the following methods:

**close**\ () -> *None*

Corresponds to `curl_easy_cleanup`_ in libcurl. This method is
automatically called by pycurl when a Curl object no longer has any
references to it, but can also be called explicitly.

**perform**\ () -> *None*

Corresponds to `curl_easy_perform`_ in libcurl.

**reset**\ () -> *None*

Corresponds to `curl_easy_reset`_ in libcurl.

**setopt**\ (*option, value*) -> *None*

Corresponds to `curl_easy_setopt`_ in libcurl, where *option* is
specified with the ``CURLOPT_*`` constants in libcurl, except that the
``CURLOPT_``
prefix has been removed. (See below for exceptions.) The type for *value*
depends on the option, and can be either a string, integer, long integer,
file object, list, or function.

Example usage:

::

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

**getinfo**\ (*option*) -> *Result*

Corresponds to `curl_easy_getinfo`_ in libcurl, where *option* is the
same as the ``CURLINFO_*`` constants in libcurl, except that the ``CURLINFO_``
prefix
has been removed. (See below for exceptions.) *Result* contains an integer,
float or string, depending on which option is given. The ``getinfo`` method
should not be called unless ``perform`` has been called and finished.

Example usage:

::

    import pycurl
    c = pycurl.Curl()
    c.setopt(pycurl.URL, "http://sf.net")
    c.setopt(pycurl.FOLLOWLOCATION, 1)
    c.perform()
    print c.getinfo(pycurl.HTTP_CODE), c.getinfo(pycurl.EFFECTIVE_URL)
    ...
    --> 200 "http://sourceforge.net/"

**pause**\ (*bitmask*) -> *None*

Corresponds to `curl_easy_pause`_ in libcurl. The argument should be
derived from the ``PAUSE_RECV``, ``PAUSE_SEND``, ``PAUSE_ALL`` and
``PAUSE_CONT`` constants.

**errstr**\ () -> *String*

Returns the internal libcurl error buffer of this handle as a string.

In order to distinguish between similarly-named CURLOPT and CURLINFO
constants, some have ``OPT_`` and ``INFO_`` prefixes. These are
``INFO_FILETIME``, ``OPT_FILETIME``, ``INFO_COOKIELIST`` (but ``setopt`` uses
``COOKIELIST``!), ``INFO_CERTINFO``, and ``OPT_CERTINFO``.

The value returned by ``getinfo(INFO_CERTINFO)`` is a list with one element
per certificate in the chain, starting with the leaf; each element is a
sequence of ``(``*key*``, ``*value*``)`` tuples.

.. _curl_easy_cleanup:
    http://curl.haxx.se/libcurl/c/curl_easy_cleanup.html
.. _curl_easy_perform:
    http://curl.haxx.se/libcurl/c/curl_easy_perform.html
.. _curl_easy_reset: http://curl.haxx.se/libcurl/c/curl_easy_reset.html
.. _curl_easy_setopt: http://curl.haxx.se/libcurl/c/curl_easy_setopt.html
.. _curl_easy_getinfo:
    http://curl.haxx.se/libcurl/c/curl_easy_getinfo.html
.. _curl_easy_pause: http://curl.haxx.se/libcurl/c/curl_easy_pause.html
