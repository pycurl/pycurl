getinfo(info) -> Result

Extract and return information from a curl session.

Corresponds to `curl_easy_getinfo`_ in libcurl, where *option* is
the same as the ``CURLINFO_*`` constants in libcurl, except that the
``CURLINFO_`` prefix has been removed. (See below for exceptions.)
*Result* contains an integer, float or string, depending on which
option is given. The ``getinfo`` method should not be called unless
``perform`` has been called and finished.

In order to distinguish between similarly-named CURLOPT and CURLINFO
constants, some have ``OPT_`` and ``INFO_`` prefixes. These are
``INFO_FILETIME``, ``OPT_FILETIME``, ``INFO_COOKIELIST`` (but ``setopt`` uses
``COOKIELIST``!), ``INFO_CERTINFO``, and ``OPT_CERTINFO``.

The value returned by ``getinfo(INFO_CERTINFO)`` is a list with one element
per certificate in the chain, starting with the leaf; each element is a
sequence of *(key, value)* tuples.

Example usage::

    import pycurl
    c = pycurl.Curl()
    c.setopt(pycurl.URL, "http://sf.net")
    c.setopt(pycurl.FOLLOWLOCATION, 1)
    c.perform()
    print c.getinfo(pycurl.HTTP_CODE), c.getinfo(pycurl.EFFECTIVE_URL)
    ...
    --> 200 "http://sourceforge.net/"


Raises pycurl.error exception upon failure.

.. _curl_easy_getinfo:
    http://curl.haxx.se/libcurl/c/curl_easy_getinfo.html
