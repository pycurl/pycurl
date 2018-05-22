getinfo(option) -> Result

Extract and return information from a curl session,
decoding string data in Python's default encoding at the time of the call.
Corresponds to `curl_easy_getinfo`_ in libcurl.
The ``getinfo`` method should not be called unless
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
  return a Python string (``str`` on Python 2 and Python 3).
  On Python 2, the string contains whatever data libcurl returned.
  On Python 3, the data returned by libcurl is decoded using the
  default string encoding at the time of the call.
  If the data cannot be decoded using the default encoding, ``UnicodeDecodeError``
  is raised. Use :ref:`getinfo_raw <getinfo_raw>`
  to retrieve the data as ``bytes`` in these
  cases.
- ``SSL_ENGINES`` and ``INFO_COOKIELIST`` return a list of strings.
  The same encoding caveats apply; use :ref:`getinfo_raw <getinfo_raw>`
  to retrieve the
  data as a list of byte strings.
- ``INFO_CERTINFO`` returns a list with one element
  per certificate in the chain, starting with the leaf; each element is a
  sequence of *(key, value)* tuples where both ``key`` and ``value`` are
  strings. String encoding caveats apply; use :ref:`getinfo_raw <getinfo_raw>`
  to retrieve
  certificate data as byte strings.

On Python 2, ``getinfo`` and ``getinfo_raw`` behave identically.

Example usage::

    import pycurl
    c = pycurl.Curl()
    c.setopt(pycurl.OPT_CERTINFO, 1)
    c.setopt(pycurl.URL, "https://python.org")
    c.setopt(pycurl.FOLLOWLOCATION, 1)
    c.perform()
    print(c.getinfo(pycurl.HTTP_CODE))
    # --> 200
    print(c.getinfo(pycurl.EFFECTIVE_URL))
    # --> "https://www.python.org/"
    certinfo = c.getinfo(pycurl.INFO_CERTINFO)
    print(certinfo)
    # --> [(('Subject', 'C = AU, ST = Some-State, O = PycURL test suite,
             CN = localhost'), ('Issuer', 'C = AU, ST = Some-State,
             O = PycURL test suite, OU = localhost, CN = localhost'),
            ('Version', '0'), ...)]


Raises pycurl.error exception upon failure.

.. _curl_easy_getinfo:
    https://curl.haxx.se/libcurl/c/curl_easy_getinfo.html
