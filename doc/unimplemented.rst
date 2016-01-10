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
