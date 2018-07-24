perform_rb() -> response_body

Perform a file transfer and return response body as a byte string.

This method arranges for response body to be saved in a StringIO
(Python 2) or BytesIO (Python 3) instance, then invokes :ref:`perform <perform>`
to perform the file transfer, then returns the value of the StringIO/BytesIO
instance which is a ``str`` instance on Python 2 and ``bytes`` instance
on Python 3. Errors during transfer raise ``pycurl.error`` exceptions
just like in :ref:`perform <perform>`.

Use :ref:`perform_rs <perform_rs>` to retrieve response body as a string
(``str`` instance on both Python 2 and 3).

Raises ``pycurl.error`` exception upon failure.

*Added in version 7.43.0.2.*
