errstr_raw() -> byte string

Return the internal libcurl error buffer of this handle as a byte string.

Return value is a ``str`` instance on Python 2 and ``bytes`` instance
on Python 3. Unlike :ref:`errstr_raw <errstr_raw>`, ``errstr_raw``
allows reading libcurl error buffer in Python 3 when its contents is not
valid in Python's default encoding.

On Python 2, ``errstr`` and ``errstr_raw`` behave identically.

*Added in version 7.43.0.2.*
