perform_rb() -> response_body

Perform a file transfer and return response body as a byte string.

This method arranges for response body to be saved in a BytesIO
instance, then invokes :ref:`perform <perform>`
to perform the file transfer, then returns the value of the BytesIO
instance which is a ``bytes`` instance. Errors during transfer raise
``pycurl.error`` exceptions just like in :ref:`perform <perform>`.

Use :ref:`perform_rs <perform_rs>` to retrieve response body as a ``str``.

Raises ``pycurl.error`` exception upon failure.

*Added in version 7.43.0.2.*
