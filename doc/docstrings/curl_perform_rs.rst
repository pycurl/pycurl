perform_rs() -> response_body

Perform a file transfer and return response body as a string.

On Python 2, this method arranges for response body to be saved in a StringIO
instance, then invokes :ref:`perform <perform>`
to perform the file transfer, then returns the value of the StringIO instance.
This behavior is identical to :ref:`perform_rb <perform_rb>`.

On Python 3, this method arranges for response body to be saved in a BytesIO
instance, then invokes :ref:`perform <perform>`
to perform the file transfer, then decodes the response body in Python's
default encoding and returns the decoded body as a Unicode string
(``str`` instance). *Note:* decoding happens after the transfer finishes,
thus an encoding error implies the transfer/network operation succeeded.

Any transfer errors raise ``pycurl.error`` exception,
just like in :ref:`perform <perform>`.

Use :ref:`perform_rb <perform_rb>` to retrieve response body as a byte
string (``bytes`` instance on Python 3) without attempting to decode it.

Raises ``pycurl.error`` exception upon failure.

*Added in version 7.43.0.2.*
