setopt(option, value) -> None

Set curl multi option. Corresponds to `curl_multi_setopt`_ in libcurl.

*option* specifies which option to set. PycURL defines constants
corresponding to ``CURLMOPT_*`` constants in libcurl, except that
the ``CURLMOPT_`` prefix is replaced with ``M_`` prefix.
For example, ``CURLMOPT_PIPELINING`` is
exposed in PycURL as ``pycurl.M_PIPELINING``. For convenience, ``CURLMOPT_*``
constants are also exposed on CurlMulti objects::

    import pycurl
    m = pycurl.CurlMulti()
    m.setopt(pycurl.M_PIPELINING, 1)
    # Same as:
    m.setopt(m.M_PIPELINING, 1)

*value* specifies the value to set the option to. Different options accept
values of different types:

- Options specified by `curl_multi_setopt`_ as accepting ``1`` or an
  integer value accept Python integers, long integers (on Python 2.x) and
  booleans::

    m.setopt(pycurl.M_PIPELINING, True)
    m.setopt(pycurl.M_PIPELINING, 1)
    # Python 2.x only:
    m.setopt(pycurl.M_PIPELINING, 1L)

- ``*FUNCTION`` options accept a function. Supported callbacks are
  ``CURLMOPT_SOCKETFUNCTION`` AND ``CURLMOPT_TIMERFUNCTION``. Please refer to
  the PycURL test suite for examples on using the callbacks.

Raises TypeError when the option value is not of a type accepted by the
respective option, and pycurl.error exception when libcurl rejects the
option or its value.

.. _curl_multi_setopt: https://curl.haxx.se/libcurl/c/curl_multi_setopt.html
