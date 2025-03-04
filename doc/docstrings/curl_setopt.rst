setopt(option, value) -> None

Set curl session option. Corresponds to `curl_easy_setopt`_ in libcurl.

*option* specifies which option to set. PycURL defines constants
corresponding to ``CURLOPT_*`` constants in libcurl, except that
the ``CURLOPT_`` prefix is removed. For example, ``CURLOPT_URL`` is
exposed in PycURL as ``pycurl.URL``, with some exceptions as detailed below.
For convenience, ``CURLOPT_*``
constants are also exposed on the Curl objects themselves::

    import pycurl
    c = pycurl.Curl()
    c.setopt(pycurl.URL, "http://www.python.org/")
    # Same as:
    c.setopt(c.URL, "http://www.python.org/")

The following are exceptions to option constant naming convention:

- ``CURLOPT_FILETIME`` is mapped as ``pycurl.OPT_FILETIME``
- ``CURLOPT_CERTINFO`` is mapped as ``pycurl.OPT_CERTINFO``
- ``CURLOPT_COOKIELIST`` is mapped as ``pycurl.COOKIELIST``
  and, as of PycURL 7.43.0.2, also as ``pycurl.OPT_COOKIELIST``
- ``CURLOPT_RTSP_CLIENT_CSEQ`` is mapped as ``pycurl.OPT_RTSP_CLIENT_CSEQ``
- ``CURLOPT_RTSP_REQUEST`` is mapped as ``pycurl.OPT_RTSP_REQUEST``
- ``CURLOPT_RTSP_SERVER_CSEQ`` is mapped as ``pycurl.OPT_RTSP_SERVER_CSEQ``
- ``CURLOPT_RTSP_SESSION_ID`` is mapped as ``pycurl.OPT_RTSP_SESSION_ID``
- ``CURLOPT_RTSP_STREAM_URI`` is mapped as ``pycurl.OPT_RTSP_STREAM_URI``
- ``CURLOPT_RTSP_TRANSPORT`` is mapped as ``pycurl.OPT_RTSP_TRANSPORT``

*value* specifies the value to set the option to. Different options accept
values of different types:

- Options specified by `curl_easy_setopt`_ as accepting ``1`` or an
  integer value accept Python integers, long integers (on Python 2.x) and
  booleans::

    c.setopt(pycurl.FOLLOWLOCATION, True)
    c.setopt(pycurl.FOLLOWLOCATION, 1)
    # Python 2.x only:
    c.setopt(pycurl.FOLLOWLOCATION, 1L)

- Options specified as accepting strings by ``curl_easy_setopt`` accept
  byte strings (``str`` on Python 2, ``bytes`` on Python 3) and
  Unicode strings with ASCII code points only.
  For more information, please refer to :ref:`unicode`. Example::

    c.setopt(pycurl.URL, "http://www.python.org/")
    c.setopt(pycurl.URL, u"http://www.python.org/")
    # Python 3.x only:
    c.setopt(pycurl.URL, b"http://www.python.org/")

- ``HTTP200ALIASES``, ``HTTPHEADER``, ``POSTQUOTE``, ``PREQUOTE``,
  ``PROXYHEADER`` and
  ``QUOTE`` accept a list or tuple of strings. The same rules apply to these
  strings as do to string option values. Example::

    c.setopt(pycurl.HTTPHEADER, ["Accept:"])
    c.setopt(pycurl.HTTPHEADER, ("Accept:",))

- ``READDATA`` accepts a file object or any Python object which has
  a ``read`` method. On Python 2, a file object will be passed directly
  to libcurl and may result in greater transfer efficiency, unless
  PycURL has been compiled with ``AVOID_STDIO`` option.
  On Python 3 and on Python 2 when the value is not a true file object,
  ``READDATA`` is emulated in PycURL via ``READFUNCTION``.
  The file should generally be opened in binary mode. Example::

    f = open('file.txt', 'rb')
    c.setopt(c.READDATA, f)

- ``WRITEDATA`` and ``WRITEHEADER`` accept a file object or any Python
  object which has a ``write`` method. On Python 2, a file object will
  be passed directly to libcurl and may result in greater transfer efficiency,
  unless PycURL has been compiled with ``AVOID_STDIO`` option.
  On Python 3 and on Python 2 when the value is not a true file object,
  ``WRITEDATA`` is emulated in PycURL via ``WRITEFUNCTION``.
  The file should generally be opened in binary mode. Example::

    f = open('/dev/null', 'wb')
    c.setopt(c.WRITEDATA, f)

- ``*FUNCTION`` options accept a function. Supported callbacks are documented
  in :ref:`callbacks`. Example::

    # Python 2
    import StringIO
    b = StringIO.StringIO()
    c.setopt(pycurl.WRITEFUNCTION, b.write)

- ``SHARE`` option accepts a :ref:`curlshareobject`.

- ``STDERR`` option is not currently supported.

It is possible to set integer options - and only them - that PycURL does
not know about by using the numeric value of the option constant directly.
For example, ``pycurl.VERBOSE`` has the value 42, and may be set as follows::

    c.setopt(42, 1)

*setopt* can reset some options to their default value, performing the job of
:py:meth:`pycurl.Curl.unsetopt`, if ``None`` is passed
for the option value. The following two calls are equivalent::

    c.setopt(c.URL, None)
    c.unsetopt(c.URL)

Raises TypeError when the option value is not of a type accepted by the
respective option, and pycurl.error exception when libcurl rejects the
option or its value.

.. _curl_easy_setopt: https://curl.haxx.se/libcurl/c/curl_easy_setopt.html
