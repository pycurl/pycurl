CurlUrl(url=None, flags=0) -> New CurlUrl object

Create a :ref:`curlurlobject` wrapping a libcurl ``CURLU`` URL handle.

Without arguments the handle is empty. If *url* is given it is parsed with
``setpart(UPART_URL, url, flags)``, so *flags* may be any combination of the
``U_*`` constants.

The component properties (``scheme``, ``host``, ``port``, ``path``, ``query``,
``fragment``, ``user``, ``password``, ``options`` and, on libcurl 7.65.0 or
later, ``zoneid``) read and write the URL parts. A getter returns ``None`` when
the part is absent. Assigning ``None`` or using ``del`` removes it. For control
over encoding and other flags use :py:meth:`~pycurl.CurlUrl.getpart` and
:py:meth:`~pycurl.CurlUrl.setpart`.

A ``CurlUrl`` can be passed to a :ref:`Curl object <curlobject>` through the
``CURLU`` option.

Corresponds to `curl_url`_ in libcurl. Requires libcurl 7.62.0 or later.

Example::

    u = pycurl.CurlUrl("https://example.com/path?a=1")
    u.host = "example.org"
    curl.setopt(pycurl.CURLU, u)

:param url: an optional URL string to parse into the new handle.
:param int flags: ``U_*`` flags controlling how *url* is parsed.

.. _curl_url: https://curl.se/libcurl/c/curl_url.html
