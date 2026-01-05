close() -> None
----------------

Close shared handle.

Corresponds to `curl_share_cleanup`_ in libcurl. This method is
automatically called by pycurl when a ``CurlShare`` object no longer has
any references to it, but can also be called explicitly.

The behavior of ``close()`` depends on the ``detach_on_close`` setting
of the ``CurlShare``:

- If ``detach_on_close`` is ``True`` (default), all associated
  :ref:`Curl objects <curlobject>` are first detached from the share
  before the share handle is closed. Detaching clears the ``SHARE``
  option on each ``Curl`` object but does not close them.

- If ``detach_on_close`` is ``False``, calling ``close()`` while there
  are still associated ``Curl`` objects raises ``pycurl.error`` and the
  share handle is not closed.

.. warning::

   Automatic detachment performed when ``detach_on_close`` is ``True``
   is **not thread-safe** with respect to the associated ``Curl``
   objects. The caller must ensure that no other thread is operating on
   those ``Curl`` objects while ``close()`` is executing.

.. _curl_share_cleanup:
    https://curl.haxx.se/libcurl/c/curl_share_cleanup.html