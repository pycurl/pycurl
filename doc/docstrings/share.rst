CurlShare(detach_on_close=True) -> New CurlShare object

Creates a new :ref:`curlshareobject` which corresponds to a
``CURLSH`` handle in libcurl. CurlShare objects is what you pass as an
argument to the SHARE option on :ref:`Curl objects <curlobject>`.

The ``CurlShare`` object can be used as a context manager. Exiting the
context calls ``close()``.

When a ``CurlShare`` is closed, its behavior depends on the value of
``detach_on_close``.

Example::

    with pycurl.CurlShare(detach_on_close=True) as s:
        curl.setopt(pycurl.SHARE, s)
        # perform operations
    # the CurlShare is closed and the Curl object has been detached

:param bool detach_on_close:
    Controls how associated :ref:`Curl objects <curlobject>` are handled
    when the ``CurlShare`` is closed.

    If ``True`` (default), all live ``Curl`` objects associated with the
    share are automatically detached when ``close()`` is called or when
    exiting the context manager. Detaching clears the ``SHARE`` option on
    each ``Curl`` object, but does **not** close them. The caller remains
    responsible for managing the lifetime of the ``Curl`` objects.

    If ``False``, calling ``close()`` (or exiting the context manager)
    while there are still ``Curl`` objects associated with the share
    raises an exception. In this mode, the caller must explicitly remove
    or close all associated ``Curl`` objects before closing the
    ``CurlShare``.

.. warning::

   Detaching ``Curl`` objects from a ``CurlShare`` is **not thread-safe**
   with respect to those ``Curl`` objects.

   The caller is responsible for ensuring proper synchronization when
   using ``CurlShare`` and ``Curl`` objects across multiple threads.