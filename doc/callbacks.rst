.. _callbacks:

Callbacks
=========

For more fine-grained control, libcurl allows a number of callbacks to be
associated with each connection. In pycurl, callbacks are defined using the
``setopt()`` method for Curl objects with options ``WRITEFUNCTION``,
``READFUNCTION``, ``HEADERFUNCTION``, ``PROGRESSFUNCTION``, ``IOCTLFUNCTION``, or
``DEBUGFUNCTION``. These options correspond to the libcurl options with ``CURLOPT_``
prefix removed. A callback in pycurl must be either a regular Python
function, a class method or an extension type function.

There are some limitations to some of the options which can be used
concurrently with the pycurl callbacks compared to the libcurl callbacks.
This is to allow different callback functions to be associated with different
Curl objects. More specifically, ``WRITEDATA`` cannot be used with
``WRITEFUNCTION``, ``READDATA`` cannot be used with ``READFUNCTION``,
``WRITEHEADER`` cannot be used with ``HEADERFUNCTION``, ``PROGRESSDATA``
cannot be used with ``PROGRESSFUNCTION``, ``IOCTLDATA``
cannot be used with ``IOCTLFUNCTION``, and ``DEBUGDATA`` cannot be used with
``DEBUGFUNCTION``. In practice, these limitations can be overcome by having a
callback function be a class instance method and rather use the class
instance attributes to store per object data such as files used in the
callbacks.

The signature of each callback used in pycurl is documented below.


WRITEFUNCTION
-------------

.. function:: WRITEFUNCTION(byte string) -> number of characters written

    Callback for writing data. Corresponds to `CURLOPT_WRITEFUNCTION`_
    in libcurl.

    On Python 3, the argument is of type ``bytes``.

    The ``WRITEFUNCTION`` callback may return the number of bytes written.
    If this number is not equal to the size of the byte string, this signifies
    an error and libcurl will abort the request. Returning ``None`` is an
    alternate way of indicating that the callback has consumed all of the
    string passed to it and, hence, succeeded.

    `write_test.py test`_ shows how to use ``WRITEFUNCTION``.


Example: Callbacks for document header and body
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This example prints the header data to stderr and the body data to stdout.
Also note that neither callback returns the number of bytes written. For
WRITEFUNCTION and HEADERFUNCTION callbacks, returning None implies that all
bytes where written.

::

    ## Callback function invoked when body data is ready
    def body(buf):
        # Print body data to stdout
        import sys
        sys.stdout.write(buf)
        # Returning None implies that all bytes were written

    ## Callback function invoked when header data is ready
    def header(buf):
        # Print header data to stderr
        import sys
        sys.stderr.write(buf)
        # Returning None implies that all bytes were written

    c = pycurl.Curl()
    c.setopt(pycurl.URL, "http://www.python.org/")
    c.setopt(pycurl.WRITEFUNCTION, body)
    c.setopt(pycurl.HEADERFUNCTION, header)
    c.perform()


HEADERFUNCTION
--------------

.. function:: HEADERFUNCTION(byte string) -> number of characters written

    Callback for writing received headers. Corresponds to
    `CURLOPT_HEADERFUNCTION`_ in libcurl.

    On Python 3, the argument is of type ``bytes``.

    The ``HEADERFUNCTION`` callback may return the number of bytes written.
    If this number is not equal to the size of the byte string, this signifies
    an error and libcurl will abort the request. Returning ``None`` is an
    alternate way of indicating that the callback has consumed all of the
    string passed to it and, hence, succeeded.

    `header_test.py test`_ shows how to use ``WRITEFUNCTION``.


READFUNCTION
------------

.. function:: READFUNCTION(number of characters to read) -> byte string

    Callback for reading data. Corresponds to `CURLOPT_READFUNCTION`_ in
    libcurl.

    On Python 3, the callback must return either a byte string or a Unicode
    string consisting of ASCII code points only.

    In addition, ``READFUNCTION`` may return ``READFUNC_ABORT`` or
    ``READFUNC_PAUSE``. See the libcurl documentation for an explanation
    of these values.

    The `file_upload.py example`_ in the distribution contains example code for
    using ``READFUNCTION``.


.. _SEEKFUNCTION:

SEEKFUNCTION
------------

.. function:: SEEKFUNCTION(offset, origin) -> status

    Callback for seek operations. Corresponds to `CURLOPT_SEEKFUNCTION`_
    in libcurl.


IOCTLFUNCTION
-------------

.. function:: IOCTLFUNCTION(ioctl cmd) -> status

    Callback for I/O operations. Corresponds to `CURLOPT_IOCTLFUNCTION`_
    in libcurl.

    *Note:* this callback is deprecated. Use :ref:`SEEKFUNCTION <SEEKFUNCTION>` instead.


DEBUGFUNCTION
-------------

.. function:: DEBUGFUNCTION(debug message type, debug message byte string) -> None

    Callback for debug information. Corresponds to `CURLOPT_DEBUGFUNCTION`_
    in libcurl.

    *Changed in version 7.19.5.2:* The second argument to a ``DEBUGFUNCTION``
    callback is now of type ``bytes`` on Python 3. Previously the argument was
    of type ``str``.

    `debug_test.py test`_ shows how to use ``DEBUGFUNCTION``.


Example: Debug callbacks
~~~~~~~~~~~~~~~~~~~~~~~~

This example shows how to use the debug callback. The debug message type is
an integer indicating the type of debug message. The VERBOSE option must be
enabled for this callback to be invoked.

::

    def test(debug_type, debug_msg):
        print "debug(%d): %s" % (debug_type, debug_msg)

    c = pycurl.Curl()
    c.setopt(pycurl.URL, "http://curl.haxx.se/")
    c.setopt(pycurl.VERBOSE, 1)
    c.setopt(pycurl.DEBUGFUNCTION, test)
    c.perform()


PROGRESSFUNCTION
----------------

.. function:: PROGRESSFUNCTION(download total, downloaded, upload total, uploaded) -> status

    Callback for progress meter. Corresponds to `CURLOPT_PROGRESSFUNCTION`_
    in libcurl.


Example: Download/upload progress callback
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This example shows how to use the progress callback. When downloading a
document, the arguments related to uploads are zero, and vice versa.

::

    ## Callback function invoked when download/upload has progress
    def progress(download_t, download_d, upload_t, upload_d):
        print "Total to download", download_t
        print "Total downloaded", download_d
        print "Total to upload", upload_t
        print "Total uploaded", upload_d

    c = pycurl.Curl()
    c.setopt(c.URL, "http://slashdot.org/")
    c.setopt(c.NOPROGRESS, 0)
    c.setopt(c.PROGRESSFUNCTION, progress)
    c.perform()


.. _CURLOPT_HEADERFUNCTION: http://curl.haxx.se/libcurl/c/CURLOPT_HEADERFUNCTION.html
.. _CURLOPT_WRITEFUNCTION: http://curl.haxx.se/libcurl/c/CURLOPT_WRITEFUNCTION.html
.. _CURLOPT_READFUNCTION: http://curl.haxx.se/libcurl/c/CURLOPT_READFUNCTION.html
.. _CURLOPT_PROGRESSFUNCTION: http://curl.haxx.se/libcurl/c/CURLOPT_PROGRESSFUNCTION.html
.. _CURLOPT_DEBUGFUNCTION: http://curl.haxx.se/libcurl/c/CURLOPT_DEBUGFUNCTION.html
.. _CURLOPT_SEEKFUNCTION: http://curl.haxx.se/libcurl/c/CURLOPT_SEEKFUNCTION.html
.. _CURLOPT_IOCTLFUNCTION: http://curl.haxx.se/libcurl/c/CURLOPT_IOCTLFUNCTION.html
.. _file_upload.py example: https://github.com/pycurl/pycurl/blob/master/examples/file_upload.py
.. _write_test.py test: https://github.com/pycurl/pycurl/blob/master/tests/write_test.py
.. _header_test.py test: https://github.com/pycurl/pycurl/blob/master/tests/header_test.py
.. _debug_test.py test: https://github.com/pycurl/pycurl/blob/master/tests/debug_test.py
