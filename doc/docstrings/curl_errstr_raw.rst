errstr_raw() -> byte string

Return the internal libcurl error buffer of this handle as a byte string.

Return value is a ``bytes`` instance. Unlike :ref:`errstr <errstr>`,
``errstr_raw`` allows reading libcurl error buffer when its contents is not
valid in Python's default encoding.

*Added in version 7.43.0.2.*
