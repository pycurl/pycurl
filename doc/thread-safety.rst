.. _thread-safety:

Thread Safety
=============

Per `libcurl thread safety documentation`_, libcurl is thread-safe but
has no internal thread synchronization.

For Python programs using PycURL, this means:

* Accessing the same PycURL object from different threads is OK when
  this object is not involved in active transfers, as Python internally
  has a Global Interpreter Lock and only one operating system thread can
  be executing Python code at a time. On free-threaded CPython, the
  GIL is no longer present; the same rules apply, but the caller must
  serialise concurrent access to a shared PycURL object explicitly.

* Accessing a PycURL object that is involved in an active transfer from
  Python code *inside a libcurl callback for the PycURL object in question*
  is OK, because PycURL takes out the appropriate locks.

* Accessing a PycURL object that is involved in an active transfer from
  Python code *outside of a libcurl callback for the PycURL object in question*
  is unsafe.

* ``CurlShare`` is thread-safe: different ``Curl`` handles attached
  to the same share may be used from different threads. Concurrent
  method calls on the same ``CurlShare`` Python object are not.

* Closing a ``CurlShare`` object with ``detach_on_close=True`` (the
  default) is **not thread-safe** with respect to the associated
  ``Curl`` objects. During ``CurlShare.close()``, PycURL automatically
  detaches all associated ``Curl`` objects by clearing their ``SHARE``
  option. The caller must ensure that no other thread is using the
  associated ``Curl`` objects while ``CurlShare.close()`` is executing.

* Not every kind of libcurl shared data is safe to share across
  threads. See `CURLSHOPT_SHARE`_ for the list of supported
  ``CURL_LOCK_DATA_*`` values and their constraints.

* A WebSocket handle (``CONNECT_ONLY=2`` plus ``ws_send`` / ``ws_recv``)
  follows the same one-handle-one-thread rule: do not call ``ws_send``
  from one thread while ``ws_recv`` runs on another. Serialise access
  with a lock. Calls from another thread while ``perform()`` is running
  are unsafe unless they happen inside that handle's active
  ``WRITEFUNCTION`` callback.

PycURL handles the necessary SSL locks for OpenSSL/LibreSSL/BoringSSL,
GnuTLS, NSS, mbedTLS and wolfSSL.

A special situation exists when libcurl uses the standard C library
name resolver (i.e., not threaded nor c-ares resolver). By default libcurl
uses signals for timeouts with the C library resolver, and signals do not
work properly in multi-threaded programs. When using PycURL objects from
multiple Python threads ``NOSIGNAL`` option `must be given`_.

.. _libcurl thread safety documentation: https://curl.haxx.se/libcurl/c/threadsafe.html
.. _CURLSHOPT_SHARE: https://curl.se/libcurl/c/CURLSHOPT_SHARE.html
.. _must be given: https://github.com/curl/curl/issues/1003
