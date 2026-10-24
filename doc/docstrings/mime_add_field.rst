add_field(name, value, content_type=None, encoder=None, headers=None) -> CurlMimePart

Add a simple form field part and return it.

Equivalent to ``add(name=name, data=value, ...)``.

:param str name: field name.
:param value: field content, as ``bytes``, an ASCII ``str``, or any object
    supporting the buffer protocol.
:param str content_type: value for the part's ``Content-Type`` header.
:param str encoder: content transfer encoding, for example ``"base64"``.
:param headers: extra headers, as a list or tuple of strings.
