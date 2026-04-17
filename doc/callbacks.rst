.. _callbacks:

Callbacks
=========

For more fine-grained control, libcurl allows a number of callbacks to be
associated with each connection. In pycurl, callbacks are defined using the
``setopt()`` method for Curl objects with options ``WRITEFUNCTION``,
``READFUNCTION``, ``HEADERFUNCTION``, ``PROGRESSFUNCTION``,
``XFERINFOFUNCTION``, ``IOCTLFUNCTION``, ``DEBUGFUNCTION``,
``PREREQFUNCTION``, ``TRAILERFUNCTION``, ``RESOLVER_START_FUNCTION``,
``FNMATCH_FUNCTION``, ``HSTSREADFUNCTION`` or ``HSTSWRITEFUNCTION``.
These options correspond to the libcurl options with ``CURLOPT_``
prefix removed. A callback in pycurl must be either a regular Python
function, a class method or an extension type function.

There are some limitations to some of the options which can be used
concurrently with the pycurl callbacks compared to the libcurl callbacks.
This is to allow different callback functions to be associated with different
Curl objects. More specifically, ``WRITEDATA`` cannot be used with
``WRITEFUNCTION``, ``READDATA`` cannot be used with ``READFUNCTION``,
``WRITEHEADER`` cannot be used with ``HEADERFUNCTION``.
In practice, these limitations can be overcome by having a
callback function be a class instance method and rather use the class
instance attributes to store per object data such as files used in the
callbacks.

The signature of each callback used in PycURL is documented below.


Error Reporting
---------------

PycURL callbacks are invoked as follows:

Python application -> ``perform()`` -> libcurl (C code) -> Python callback

Because callbacks are invoked by libcurl, they should not raise exceptions
on failure but instead return appropriate values indicating failure.
The documentation for individual callbacks below specifies expected success and
failure return values.

Unhandled exceptions propagated out of Python callbacks will be intercepted
by PycURL or the Python runtime. This will fail the callback with a
generic failure status, in turn failing the ``perform()`` operation.
A failing ``perform()`` will raise ``pycurl.error``, but the error code
used depends on the specific callback.

``KeyboardInterrupt`` and other ``BaseException`` subclasses (for example, ``SystemExit``)
are handled specially: if they are raised inside a callback, they are preserved and re-raised
to the caller instead of being converted into a ``pycurl.error``.

Rich context information like exception objects can be stored in various ways,
for example the following example stores OPENSOCKET callback exception on the
Curl object::

    import pycurl, random, socket

    class ConnectionRejected(Exception):
        pass

    def opensocket(curl, purpose, curl_address):
        # always fail
        curl.exception = ConnectionRejected('Rejecting connection attempt in opensocket callback')
        return pycurl.SOCKET_BAD

        # the callback must create a socket if it does not fail,
        # see examples/opensocketexception.py

    c = pycurl.Curl()
    c.setopt(c.URL, 'http://pycurl.io')
    c.exception = None
    c.setopt(c.OPENSOCKETFUNCTION,
        lambda purpose, address: opensocket(c, purpose, address))

    try:
        c.perform()
    except pycurl.error as e:
        if e.args[0] == pycurl.E_COULDNT_CONNECT and c.exception:
            print(c.exception)
        else:
            print(e)


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

    The callback must return either a C-contiguous object supporting
    the buffer protocol (e.g. `bytes`, `bytearray`, `memoryview`, or a
    C-contiguous `numpy` array) or a Unicode string consisting of ASCII code
    points only.

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

    ``origin`` is ``0`` (beginning), ``1`` (current position) or ``2`` (end).

    Return one of:

    - ``SEEKFUNC_OK`` (seek succeeded)
    - ``SEEKFUNC_FAIL`` (hard failure)
    - ``SEEKFUNC_CANTSEEK`` (seek not possible; libcurl may fall back)


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
        print("debug(%d): %s" % (debug_type, debug_msg))

    c = pycurl.Curl()
    c.setopt(pycurl.URL, "https://curl.haxx.se/")
    c.setopt(pycurl.VERBOSE, 1)
    c.setopt(pycurl.DEBUGFUNCTION, test)
    c.perform()


PROGRESSFUNCTION
----------------

.. function:: PROGRESSFUNCTION(download total, downloaded, upload total, uploaded) -> status

    Callback for progress meter. Corresponds to `CURLOPT_PROGRESSFUNCTION`_
    in libcurl.

    ``PROGRESSFUNCTION`` receives amounts as floating point arguments to the
    callback. Since libcurl 7.32.0 ``PROGRESSFUNCTION`` is deprecated;
    ``XFERINFOFUNCTION`` should be used instead which receives amounts as
    long integers.

    ``NOPROGRESS`` option must be set for False libcurl to invoke a
    progress callback, as PycURL by default sets ``NOPROGRESS`` to True.


XFERINFOFUNCTION
----------------

.. function:: XFERINFOFUNCTION(download total, downloaded, upload total, uploaded) -> status

    Callback for progress meter. Corresponds to `CURLOPT_XFERINFOFUNCTION`_
    in libcurl.

    ``XFERINFOFUNCTION`` receives amounts as long integers.

    ``NOPROGRESS`` option must be set for False libcurl to invoke a
    progress callback, as PycURL by default sets ``NOPROGRESS`` to True.


Example: Download/upload progress callback
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This example shows how to use the progress callback. When downloading a
document, the arguments related to uploads are zero, and vice versa.

::

    ## Callback function invoked when download/upload has progress
    def progress(download_t, download_d, upload_t, upload_d):
        print("Total to download", download_t)
        print("Total downloaded", download_d)
        print("Total to upload", upload_t)
        print("Total uploaded", upload_d)

    c = pycurl.Curl()
    c.setopt(c.URL, "http://slashdot.org/")
    c.setopt(c.NOPROGRESS, False)
    c.setopt(c.XFERINFOFUNCTION, progress)
    c.perform()


OPENSOCKETFUNCTION
------------------

.. function:: OPENSOCKETFUNCTION(purpose, address) -> int

    Callback for opening sockets. Corresponds to
    `CURLOPT_OPENSOCKETFUNCTION`_ in libcurl.

    *purpose* is a ``SOCKTYPE_*`` value.

    *address* is a `namedtuple`_ with ``family``, ``socktype``, ``protocol``
    and ``addr`` fields, per `CURLOPT_OPENSOCKETFUNCTION`_ documentation.

    *addr* is an object representing the address. Currently the following
    address families are supported:

    - ``AF_INET``: *addr* is a 2-tuple of ``(host, port)``.
    - ``AF_INET6``: *addr* is a 4-tuple of ``(host, port, flow info, scope id)``.
    - ``AF_UNIX``: *addr* is a byte string containing path to the Unix socket.

      Availability: Unix.

    This behavior matches that of Python's `socket module`_.

    The callback should return a socket object, a socket file descriptor
    or a Python object with a ``fileno`` property containing the socket
    file descriptor.

    The callback may be unset by calling :ref:`setopt <setopt>` with ``None``
    as the value or by calling :ref:`unsetopt <unsetopt>`.

    `open_socket_cb_test.py test`_ shows how to use ``OPENSOCKETFUNCTION``.

    *Changed in version 7.21.5:* Previously, the callback received ``family``,
    ``socktype``, ``protocol`` and ``addr`` parameters (``purpose`` was
    not passed and ``address`` was flattened). Also, ``AF_INET6`` addresses
    were exposed as 2-tuples of ``(host, port)`` rather than 4-tuples.

    *Changed in version 7.19.3:* ``addr`` parameter added to the callback.


CLOSESOCKETFUNCTION
-------------------

.. function:: CLOSESOCKETFUNCTION(curlfd) -> int

    Callback for setting socket options. Corresponds to
    `CURLOPT_CLOSESOCKETFUNCTION`_ in libcurl.

    *curlfd* is the file descriptor to be closed.

    The callback should return an ``int``.

    The callback may be unset by calling :ref:`setopt <setopt>` with ``None``
    as the value or by calling :ref:`unsetopt <unsetopt>`.

    `close_socket_cb_test.py test`_ shows how to use ``CLOSESOCKETFUNCTION``.


SOCKOPTFUNCTION
---------------

.. function:: SOCKOPTFUNCTION(curlfd, purpose) -> int

    Callback for setting socket options. Corresponds to `CURLOPT_SOCKOPTFUNCTION`_
    in libcurl.

    *curlfd* is the file descriptor of the newly created socket.

    *purpose* is a ``SOCKTYPE_*`` value.

    The callback should return an ``int``.

    The callback may be unset by calling :ref:`setopt <setopt>` with ``None``
    as the value or by calling :ref:`unsetopt <unsetopt>`.

    `sockopt_cb_test.py test`_ shows how to use ``SOCKOPTFUNCTION``.


SSH_KEYFUNCTION
---------------

.. function:: SSH_KEYFUNCTION(known_key, found_key, match) -> int

    Callback for known host matching logic. Corresponds to
    `CURLOPT_SSH_KEYFUNCTION`_ in libcurl.

    *known_key* and *found_key* are instances of ``KhKey`` class which is a
    `namedtuple`_ with ``key`` and ``keytype`` fields, corresponding to
    libcurl's ``struct curl_khkey``::

        KhKey = namedtuple('KhKey', ('key', 'keytype'))

    The *key* field of ``KhKey`` is ``bytes``. *keytype* is an ``int``.

    *known_key* may be ``None`` when there is no known matching host key.

    ``SSH_KEYFUNCTION`` callback should return a ``KHSTAT_*`` value.

    The callback may be unset by calling :ref:`setopt <setopt>` with ``None``
    as the value or by calling :ref:`unsetopt <unsetopt>`.

    `ssh_key_cb_test.py test`_ shows how to use ``SSH_KEYFUNCTION``.


TIMERFUNCTION
-------------

.. function:: TIMERFUNCTION(timeout_ms) -> None

    Callback for installing a timer requested by libcurl. Corresponds to
    `CURLMOPT_TIMERFUNCTION`_.

    The application should arrange for a non-repeating timer to fire in
    ``timeout_ms`` milliseconds, at which point the application should call
    either :ref:`socket_action <multi-socket_action>` or
    :ref:`perform <multi-perform>`.

    See ``examples/multi-socket_action-select.py`` for an example program
    that uses the timer function and the socket function.


SOCKETFUNCTION
--------------

.. function:: SOCKETFUNCTION(what, sock_fd, multi, socketp) -> None

    Callback notifying the application about activity on libcurl sockets.
    Corresponds to `CURLMOPT_SOCKETFUNCTION`_.

    Note that the PycURL callback takes ``what`` as the first argument and
    ``sock_fd`` as the second argument, whereas the libcurl callback takes
    ``sock_fd`` as the first argument and ``what`` as the second argument.

    The ``userp`` ("private callback pointer") argument, as described in the
    ``CURLMOPT_SOCKETFUNCTION`` documentation, is set to the ``CurlMulti``
    instance.

    The ``socketp`` ("private socket pointer") argument, as described in the
    ``CURLMOPT_SOCKETFUNCTION`` documentation, is set to the value provided
    to the :ref:`assign <multi-assign>` method for the corresponding
    ``sock_fd``, or ``None`` if no value was assigned.

    See ``examples/multi-socket_action-select.py`` for an example program
    that uses the timer function and the socket function.


PREREQFUNCTION
---------------

.. function:: PREREQFUNCTION(conn_primary_ip, conn_local_ip, conn_primary_port, conn_local_port) -> int

    Callback called when a connection has been established, but before a
    request has been made. Corresponds to `CURLOPT_PREREQFUNCTION`_ in libcurl.

    *conn_primary_ip* is the primary IP address of the remote server established with this connection (as a string).

    *conn_local_ip* is the originating IP address for this connection (as a string).

    *conn_primary_port* is the primary port number on the remote server established with this connection.

    *conn_local_port* is the originating port number for this connection.

    The callback should return an ``int``, which must be either ``PREREQFUNC_OK`` (on success) or ``PREREQFUNC_ABORT`` to cause the transfer to fail with result ``ABORTED_BY_CALLBACK``.

    The callback may be unset by calling :ref:`setopt <setopt>` with ``None``
    as the value or by calling :ref:`unsetopt <unsetopt>`.

    `prereq_cb_test.py test`_ shows how to use ``PREREQFUNCTION``.


TRAILERFUNCTION
---------------

.. function:: TRAILERFUNCTION() -> list of strings or None

    Callback for supplying HTTP trailing headers on chunked uploads.
    Corresponds to `CURLOPT_TRAILERFUNCTION`_ in libcurl.

    The callback takes no arguments and should return either ``None``
    (no trailing headers) or a list or tuple of header strings in
    ``"Name: value"`` form. The same rules apply to these strings as
    do to ``HTTPHEADER`` entries.

    Raising an exception from the callback, or returning any other type,
    causes the transfer to fail with ``TRAILERFUNC_ABORT``.

    The callback may be unset by calling :ref:`setopt <setopt>` with ``None``
    as the value or by calling :ref:`unsetopt <unsetopt>`.


RESOLVER_START_FUNCTION
-----------------------

.. function:: RESOLVER_START_FUNCTION() -> int

    Callback invoked before each name resolution. Corresponds to
    `CURLOPT_RESOLVER_START_FUNCTION`_ in libcurl.

    The callback takes no arguments. Return ``0`` (or ``None``) to let the
    resolution proceed; return any non-zero value to abort the transfer.

    The callback may be unset by calling :ref:`setopt <setopt>` with ``None``
    as the value or by calling :ref:`unsetopt <unsetopt>`.


FNMATCH_FUNCTION
----------------

.. function:: FNMATCH_FUNCTION(pattern, string) -> int

    Callback for wildcard matching used by the FTP wildcard transfer
    feature. Corresponds to `CURLOPT_FNMATCH_FUNCTION`_ in libcurl.

    *pattern* and *string* are both ``bytes``.

    The callback should return one of:

    - ``FNMATCHFUNC_MATCH`` (pattern matched)
    - ``FNMATCHFUNC_NOMATCH`` (pattern did not match)
    - ``FNMATCHFUNC_FAIL`` (error during matching; aborts the transfer)

    The callback may be unset by calling :ref:`setopt <setopt>` with ``None``
    as the value or by calling :ref:`unsetopt <unsetopt>`.


HSTSWRITEFUNCTION
-----------------

.. function:: HSTSWRITEFUNCTION(entry, index) -> int

    Callback for persisting the in-memory HSTS cache. Corresponds to
    `CURLOPT_HSTSWRITEFUNCTION`_ in libcurl. Requires ``HSTS_CTRL`` to be
    set to ``CURLHSTS_ENABLE``.

    *entry* is an ``HstsEntry`` `namedtuple`_ with ``host``, ``expire``
    and ``include_subdomains`` fields::

        HstsEntry = namedtuple('HstsEntry',
                               ('host', 'expire', 'include_subdomains'))

    *host* is ``bytes``. *expire* is a tz-aware ``datetime`` in UTC, or
    ``None`` when the entry never expires. *include_subdomains* is ``bool``.

    *index* is an ``HstsIndex`` `namedtuple`_ indicating progress through
    the cache::

        HstsIndex = namedtuple('HstsIndex', ('index', 'total'))

    The callback should return ``CURLSTS_OK`` (entry accepted),
    ``CURLSTS_DONE`` (stop iterating) or ``CURLSTS_FAIL`` (error).
    Returning ``None`` is equivalent to ``CURLSTS_OK``.

    libcurl invokes the callback during ``perform()`` and during handle
    cleanup; exceptions raised inside the callback while the handle is
    being cleaned up are written to :py:data:`sys.unraisablehook` and
    do not propagate.

    The callback may be unset by calling :ref:`setopt <setopt>` with ``None``
    as the value or by calling :ref:`unsetopt <unsetopt>`.


HSTSREADFUNCTION
----------------

.. function:: HSTSREADFUNCTION() -> HstsEntry or None

    Callback for preloading the in-memory HSTS cache. Corresponds to
    `CURLOPT_HSTSREADFUNCTION`_ in libcurl. Requires ``HSTS_CTRL`` to be
    set to ``CURLHSTS_ENABLE``.

    The callback takes no arguments. It is invoked repeatedly until it
    returns ``None``.

    Return ``None`` to signal there are no more entries
    (``CURLSTS_DONE``), or an ``HstsEntry`` (or any 3-tuple) where:

    - *host* is ``bytes`` or an ASCII ``str``.
    - *expire* is a ``datetime`` or ``None``. ``None`` means the entry
      never expires. Aware datetimes are converted to UTC; naive
      datetimes are interpreted as UTC.
    - *include_subdomains* is any truthy/falsy value.

    Raising an exception or returning anything else causes the transfer
    to fail with ``CURLSTS_FAIL``.

    The callback may be unset by calling :ref:`setopt <setopt>` with ``None``
    as the value or by calling :ref:`unsetopt <unsetopt>`.


WebSocket callback receive (libcurl 7.86.0 or later)
----------------------------------------------------

libcurl supports two WebSocket usage models: *detached mode*
(``CONNECT_ONLY=2`` plus ``ws_send`` / ``ws_recv``, documented on the
:ref:`Curl object <curlobject>`) and *callback-receive mode*, where
libcurl drives the transfer and delivers each received frame chunk
through the ordinary ``WRITEFUNCTION`` callback. No separate callback
registration is required — set ``WRITEFUNCTION`` on a ``ws://`` /
``wss://`` URL, leave ``CONNECT_ONLY`` unset, and call
:ref:`perform <perform>` as you would for any other transfer.
``perform()`` blocks for the full lifetime of the WebSocket connection
and returns when the peer closes (or the transfer otherwise terminates),
so the server side must have a predictable end condition.

Inside the callback, :py:meth:`pycurl.Curl.ws_meta` returns a ``WsFrame``
namedtuple (``age``, ``flags``, ``offset``, ``bytesleft``, ``len``)
describing the chunk currently being delivered. The ``flags`` field is
a bitmask of ``WS_TEXT``, ``WS_BINARY``, ``WS_CONT``, ``WS_PING``,
``WS_PONG``, ``WS_CLOSE``, and ``WS_OFFSET``.

libcurl's ``curl_ws_meta()`` returns ``NULL`` outside the valid
callback context; PycURL maps that to Python ``None``. The same
``ws_meta()`` method is safe to call after ``perform()`` has returned
(it simply returns ``None``) and in detached mode (likewise).

Calling :py:meth:`ws_send` or :py:meth:`ws_close` from inside the
``WRITEFUNCTION`` is allowed: libcurl treats the call as a blocking send
and returns only once the frame has been fully written (or an error
occurs). ``CURLE_AGAIN`` / ``BlockingIOError`` semantics do not apply in
this context. That relaxation applies only inside the callback itself;
calls from another thread while ``perform()`` is running are still
rejected. :py:meth:`ws_recv` and :py:meth:`ws_recv_into` remain
detached-only and still raise ``pycurl.error`` while ``perform()`` is
running.

Example::

    import pycurl

    c = pycurl.Curl()

    def on_ws_chunk(data):
        meta = c.ws_meta()           # valid only inside this callback
        if meta is not None and meta.flags & pycurl.WS_TEXT:
            print("text chunk:", data)
            c.ws_send(b"ack", pycurl.WS_BINARY)   # blocking send
        return len(data)

    c.setopt(c.URL, "wss://example.com/socket")
    c.setopt(c.WRITEFUNCTION, on_ws_chunk)
    c.perform()                       # blocks until peer closes
    c.close()

`ws_callback.py example`_ is a complete runnable version.


.. _CURLOPT_HEADERFUNCTION: https://curl.haxx.se/libcurl/c/CURLOPT_HEADERFUNCTION.html
.. _CURLOPT_WRITEFUNCTION: https://curl.haxx.se/libcurl/c/CURLOPT_WRITEFUNCTION.html
.. _CURLOPT_READFUNCTION: https://curl.haxx.se/libcurl/c/CURLOPT_READFUNCTION.html
.. _CURLOPT_PROGRESSFUNCTION: https://curl.haxx.se/libcurl/c/CURLOPT_PROGRESSFUNCTION.html
.. _CURLOPT_XFERINFOFUNCTION: https://curl.haxx.se/libcurl/c/CURLOPT_XFERINFOFUNCTION.html
.. _CURLOPT_DEBUGFUNCTION: https://curl.haxx.se/libcurl/c/CURLOPT_DEBUGFUNCTION.html
.. _CURLOPT_SEEKFUNCTION: https://curl.haxx.se/libcurl/c/CURLOPT_SEEKFUNCTION.html
.. _CURLOPT_IOCTLFUNCTION: https://curl.haxx.se/libcurl/c/CURLOPT_IOCTLFUNCTION.html
.. _file_upload.py example: https://github.com/pycurl/pycurl/blob/master/examples/file_upload.py
.. _write_test.py test: https://github.com/pycurl/pycurl/blob/master/tests/write_test.py
.. _header_test.py test: https://github.com/pycurl/pycurl/blob/master/tests/header_test.py
.. _debug_test.py test: https://github.com/pycurl/pycurl/blob/master/tests/debug_test.py
.. _CURLOPT_SSH_KEYFUNCTION: https://curl.haxx.se/libcurl/c/CURLOPT_SSH_KEYFUNCTION.html
.. _namedtuple: https://docs.python.org/library/collections.html#collections.namedtuple
.. _CURLOPT_SOCKOPTFUNCTION: https://curl.haxx.se/libcurl/c/CURLOPT_SOCKOPTFUNCTION.html
.. _sockopt_cb_test.py test: https://github.com/pycurl/pycurl/blob/master/tests/sockopt_cb_test.py
.. _ssh_key_cb_test.py test: https://github.com/pycurl/pycurl/blob/master/tests/ssh_key_cb_test.py
.. _CURLOPT_CLOSESOCKETFUNCTION: https://curl.haxx.se/libcurl/c/CURLOPT_CLOSESOCKETFUNCTION.html
.. _close_socket_cb_test.py test: https://github.com/pycurl/pycurl/blob/master/tests/close_socket_cb_test.py
.. _CURLOPT_OPENSOCKETFUNCTION: https://curl.haxx.se/libcurl/c/CURLOPT_OPENSOCKETFUNCTION.html
.. _open_socket_cb_test.py test: https://github.com/pycurl/pycurl/blob/master/tests/open_socket_cb_test.py
.. _socket module: https://docs.python.org/library/socket.html
.. _CURLMOPT_TIMERFUNCTION: https://curl.se/libcurl/c/CURLMOPT_TIMERFUNCTION.html
.. _CURLMOPT_SOCKETFUNCTION: https://curl.se/libcurl/c/CURLMOPT_SOCKETFUNCTION.html
.. _CURLOPT_PREREQFUNCTION: https://curl.se/libcurl/c/CURLOPT_PREREQFUNCTION.html
.. _prereq_cb_test.py test: https://github.com/pycurl/pycurl/blob/master/tests/prereq_cb_test.py
.. _CURLOPT_TRAILERFUNCTION: https://curl.se/libcurl/c/CURLOPT_TRAILERFUNCTION.html
.. _CURLOPT_RESOLVER_START_FUNCTION: https://curl.se/libcurl/c/CURLOPT_RESOLVER_START_FUNCTION.html
.. _CURLOPT_FNMATCH_FUNCTION: https://curl.se/libcurl/c/CURLOPT_FNMATCH_FUNCTION.html
.. _CURLOPT_HSTSREADFUNCTION: https://curl.se/libcurl/c/CURLOPT_HSTSREADFUNCTION.html
.. _CURLOPT_HSTSWRITEFUNCTION: https://curl.se/libcurl/c/CURLOPT_HSTSWRITEFUNCTION.html
.. _ws_callback.py example: https://github.com/pycurl/pycurl/blob/master/examples/ws_callback.py
