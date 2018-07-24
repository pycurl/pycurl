getinfo_raw(option) -> Result

Extract and return information from a curl session,
returning string data as byte strings.
Corresponds to `curl_easy_getinfo`_ in libcurl.
The ``getinfo_raw`` method should not be called unless
``perform`` has been called and finished.

*option* is a constant corresponding to one of the
``CURLINFO_*`` constants in libcurl. Most option constant names match
the respective ``CURLINFO_*`` constant names with the ``CURLINFO_`` prefix
removed, for example ``CURLINFO_CONTENT_TYPE`` is accessible as
``pycurl.CONTENT_TYPE``. Exceptions to this rule are as follows:

- ``CURLINFO_FILETIME`` is mapped as ``pycurl.INFO_FILETIME``
- ``CURLINFO_COOKIELIST`` is mapped as ``pycurl.INFO_COOKIELIST``
- ``CURLINFO_CERTINFO`` is mapped as ``pycurl.INFO_CERTINFO``
- ``CURLINFO_RTSP_CLIENT_CSEQ`` is mapped as ``pycurl.INFO_RTSP_CLIENT_CSEQ``
- ``CURLINFO_RTSP_CSEQ_RECV`` is mapped as ``pycurl.INFO_RTSP_CSEQ_RECV``
- ``CURLINFO_RTSP_SERVER_CSEQ`` is mapped as ``pycurl.INFO_RTSP_SERVER_CSEQ``
- ``CURLINFO_RTSP_SESSION_ID`` is mapped as ``pycurl.INFO_RTSP_SESSION_ID``

The type of return value depends on the option, as follows:

- Options documented by libcurl to return an integer value return a
  Python integer (``long`` on Python 2, ``int`` on Python 3).
- Options documented by libcurl to return a floating point value
  return a Python ``float``.
- Options documented by libcurl to return a string value
  return a Python byte string (``str`` on Python 2, ``bytes`` on Python 3).
  The string contains whatever data libcurl returned.
  Use :ref:`getinfo <getinfo>` to retrieve this data as a Unicode string on Python 3.
- ``SSL_ENGINES`` and ``INFO_COOKIELIST`` return a list of byte strings.
  The same encoding caveats apply; use :ref:`getinfo <getinfo>` to retrieve the
  data as a list of potentially Unicode strings.
- ``INFO_CERTINFO`` returns a list with one element
  per certificate in the chain, starting with the leaf; each element is a
  sequence of *(key, value)* tuples where both ``key`` and ``value`` are
  byte strings. String encoding caveats apply; use :ref:`getinfo <getinfo>`
  to retrieve
  certificate data as potentially Unicode strings.

On Python 2, ``getinfo`` and ``getinfo_raw`` behave identically.

Example usage::

    import pycurl
    c = pycurl.Curl()
    c.setopt(pycurl.OPT_CERTINFO, 1)
    c.setopt(pycurl.URL, "https://python.org")
    c.setopt(pycurl.FOLLOWLOCATION, 1)
    c.perform()
    print(c.getinfo_raw(pycurl.HTTP_CODE))
    # --> 200
    print(c.getinfo_raw(pycurl.EFFECTIVE_URL))
    # --> b"https://www.python.org/"
    certinfo = c.getinfo_raw(pycurl.INFO_CERTINFO)
    print(certinfo)
    # --> [((b'Subject', b'C = AU, ST = Some-State, O = PycURL test suite,
             CN = localhost'), (b'Issuer', b'C = AU, ST = Some-State,
             O = PycURL test suite, OU = localhost, CN = localhost'),
            (b'Version', b'0'), ...)]


Raises pycurl.error exception upon failure.

*Added in version 7.43.0.2.*

.. _curl_easy_getinfo:
    https://curl.haxx.se/libcurl/c/curl_easy_getinfo.html
