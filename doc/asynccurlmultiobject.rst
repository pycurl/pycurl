.. _asynccurlmultiobject:

AsyncCurlMulti Object
=====================

.. note::

    The ``AsyncCurlMulti`` API is experimental and may change in a
    future release.

.. autoclass:: pycurl.AsyncCurlMulti

    AsyncCurlMulti objects have the following methods:

    .. automethod:: pycurl.AsyncCurlMulti.__init__

    .. automethod:: pycurl.AsyncCurlMulti.setopt

    .. automethod:: pycurl.AsyncCurlMulti.add_handle

    .. automethod:: pycurl.AsyncCurlMulti.remove_handle

    .. automethod:: pycurl.AsyncCurlMulti.perform

    .. automethod:: pycurl.AsyncCurlMulti.futures

    .. automethod:: pycurl.AsyncCurlMulti.aclose

    .. autoattribute:: pycurl.AsyncCurlMulti.closed

    .. automethod:: pycurl.AsyncCurlMulti.__aenter__

    .. automethod:: pycurl.AsyncCurlMulti.__aexit__
