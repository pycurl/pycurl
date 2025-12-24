CurlMulti(close_handles=False) -> New CurlMulti object

Creates a new :ref:`curlmultiobject` which corresponds to
a ``CURLM`` handle in libcurl.

The ``CurlMulti`` object can be used as a context manager. Exiting the
context calls ``close()``.

Example::

    with pycurl.CurlMulti(close_handles=True) as m:
        m.add_handle(curl)
        # perform multi operations
    # easy handles have been removed and closed

:param bool close_handles:
    If ``False`` (default), easy handles added to the multi handle
    are removed from the multi handle when ``close()`` is called
    or when exiting the context manager, but remain open and must
    be managed by the caller.

    If ``True``, easy handles are removed from the multi handle when
    ``close()`` is called or when exiting the context manager, and
    are then automatically closed.

    In all cases, easy handles are not closed when they are removed
    individually from the multi handle.
