errstr() -> string

Return the internal libcurl error buffer of this handle as a string.

Return value is a ``str`` instance. Error buffer data is decoded using
Python's default encoding at the time of the call. If this decoding fails,
``UnicodeDecodeError`` is raised. Use :ref:`errstr_raw <errstr_raw>` to
retrieve the error buffer as a byte string in this case.
