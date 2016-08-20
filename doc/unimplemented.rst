Unimplemented Options And Constants
===================================

PycURL intentionally does not expose some of the libcurl options and constants.
This document explains libcurl symbols that were omitted from PycURL.


``*DATA`` options
-----------------

In libcurl, the ``*aDATA`` options set *client data* for various callbacks.
Each callback has a corresponding ``*DATA`` option.

In Python - a language with closures - such options are unnecessary.
For example, the following code invokes an instance's ``write`` method
which has full access to its class instance::

    class Writer(object):
        def __init__(self):
            self.foo = True

        def write(chunk):
            # can use self.foo

    writer = Writer()
    curl = pycurl.Curl()
    curl.setopt(curl.WRITEFUNCTION, writer.write)

As of version 7.19.3, PycURL does implement three ``*DATA`` options for
convenience:
``WRITEDATA``, ``HEADERDATA`` and ``READDATA``. These are equivalent to
setting the respective callback option with either a ``write`` or ``read``
method, as appropriate::

    # equivalent pairs:
    curl.setopt(curl.WRITEDATA, writer)
    curl.setopt(curl.WRITEFUNCTION, writer.write)

    curl.setopt(curl.HEADERDATA, writer)
    curl.setopt(curl.HEADERFUNCTION, writer.write)

    curl.setopt(curl.READDATA, reader)
    curl.setopt(curl.READFUNCTION, reader.read)


``CURLINFO_TLS_SESSION``
------------------------

It is unclear how the SSL context should be exposed to Python code.
This option can be implemented if it finds a use case.



Undocumented symbols
--------------------

Some symbols are present in libcurl's `symbols in versions`_ document but
are not documented by libcurl. These symbols are not impemented by PycURL.

As of this writing, the following symbols are thusly omitted:

- ``CURLPAUSE_RECV_CONT``
- ``CURLPAUSE_SEND_CONT``

.. _symbols in versions: https://curl.haxx.se/libcurl/c/symbols-in-versions.html
