close() -> None

Close shared handle.

Corresponds to `curl_share_cleanup`_ in libcurl. This method is
automatically called by pycurl when a ``CurlShare`` object no longer has
any references to it, but can also be called explicitly.

The behavior of ``close()`` depends on the ``detach_on_close`` setting
of the ``CurlShare``:

- If ``detach_on_close`` is ``True`` (default), all associated idle
  :ref:`Curl objects <curlobject>` are first detached from the share
  before the share handle is closed. Detaching clears the ``SHARE``
  option on each ``Curl`` object but does not close them.

- If ``detach_on_close`` is ``False``, calling ``close()`` while there
  are still associated ``Curl`` objects raises ``pycurl.error`` and the
  share handle is not closed.

``close()`` refuses to detach a ``Curl`` handle that is currently
inside ``perform()`` and raises ``pycurl.error`` in that case, even
with ``detach_on_close=True``. Idle attached handles are still
detached automatically.

.. warning::

   Detaching ``Curl`` objects from a ``CurlShare`` is **not thread-safe**
   with respect to those ``Curl`` objects.

   The caller is responsible for ensuring proper synchronization when
   using ``CurlShare`` and ``Curl`` objects across multiple threads.

.. _curl_share_cleanup:
    https://curl.haxx.se/libcurl/c/curl_share_cleanup.html
