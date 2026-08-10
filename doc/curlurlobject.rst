.. _curlurlobject:

CurlUrl Object
==============

.. autoclass:: pycurl.CurlUrl

    A ``CurlUrl`` wraps a libcurl ``CURLU`` handle and exposes libcurl's URL
    API. It requires libcurl 7.62.0 or later.

    Component getters return ``None`` when the part is absent, which is how an
    absent part differs from an empty one. By default the properties read and
    write the raw value with no percent-encoding or decoding. Use
    :py:meth:`~pycurl.CurlUrl.getpart` and :py:meth:`~pycurl.CurlUrl.setpart`
    with the ``U_*`` flags for encoding control.

    CurlUrl objects have the following methods:

    .. automethod:: pycurl.CurlUrl.getpart

    .. automethod:: pycurl.CurlUrl.setpart

    CurlUrl objects have the following attributes:

    .. autoattribute:: pycurl.CurlUrl.url

    .. autoattribute:: pycurl.CurlUrl.scheme

    .. autoattribute:: pycurl.CurlUrl.user

    .. autoattribute:: pycurl.CurlUrl.password

    .. autoattribute:: pycurl.CurlUrl.options

    .. autoattribute:: pycurl.CurlUrl.host

    .. autoattribute:: pycurl.CurlUrl.port

    .. autoattribute:: pycurl.CurlUrl.path

    .. autoattribute:: pycurl.CurlUrl.query

    .. autoattribute:: pycurl.CurlUrl.fragment

    .. autoattribute:: pycurl.CurlUrl.zoneid

A ``CurlUrl`` can drive a transfer when passed to a :ref:`Curl object
<curlobject>` through the ``CURLU`` option, which requires libcurl 7.63.0 or
later::

    u = pycurl.CurlUrl("https://example.com/")
    curl.setopt(pycurl.CURLU, u)

libcurl reads the handle for each transfer, so a ``CurlUrl`` updated between
transfers takes effect on the next one. The ``Curl`` object keeps the ``CurlUrl``
alive while the option is set. Corresponds to `CURLOPT_CURLU`_ in libcurl.

See `libcurl-url`_ for an overview of the libcurl URL API.

.. _CURLOPT_CURLU: https://curl.se/libcurl/c/CURLOPT_CURLU.html

.. _libcurl-url: https://curl.se/libcurl/c/libcurl-url.html
