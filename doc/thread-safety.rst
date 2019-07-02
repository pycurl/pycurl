.. _thread-safety:

Thread Safety
=============

Per `libcurl thread safety documentation`_, libcurl is thread-safe but
has no internal thread synchronization.

For Python programs using PycURL, this means:

* Accessing the same PycURL object from different threads is OK when
  this object is not involved in active transfers, as Python internally
  has a Global Interpreter Lock and only one operating system thread can
  be executing Python code at a time.

* Accessing a PycURL object that is involved in an active transfer from
  Python code *inside a libcurl callback for the PycURL object in question*
  is OK, because PycURL takes out the appropriate locks.

* Accessing a PycURL object that is involved in an active transfer from
  Python code *outside of a libcurl callback for the PycURL object in question*
  is unsafe.

PycURL handles the necessary SSL locks for OpenSSL/LibreSSL/BoringSSL,
GnuTLS, NSS, mbedTLS and wolfSSL.

A special situation exists when libcurl uses the standard C library
name resolver (i.e., not threaded nor c-ares resolver). By default libcurl
uses signals for timeouts with the C library resolver, and signals do not
work properly in multi-threaded programs. When using PycURL objects from
multiple Python threads ``NOSIGNAL`` option `must be given`_.

.. _libcurl thread safety documentation: https://curl.haxx.se/libcurl/c/threadsafe.html
.. _must be given: https://github.com/curl/curl/issues/1003
