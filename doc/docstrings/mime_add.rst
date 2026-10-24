add(name=None, data=None, file=None, filename=None, content_type=None, headers=None, encoder=None) -> CurlMimePart

Add a part and set the given fields on it, then return it.

At most one of *data* and *file* may be given. Each argument that is not
``None`` is applied with the ``CurlMimePart`` method of the same name,
except *file* and *content_type*, which use ``filedata()`` and ``type()``.

:param str name: part name. A byte string is also accepted.
:param data: in-memory content, as ``bytes``, an ASCII ``str``, or any object
    supporting the buffer protocol.
:param str file: path to read the content from, instead of *data*.
:param str filename: remote filename to report for the part.
:param str content_type: value for the part's ``Content-Type`` header.
:param headers: extra headers, as a list or tuple of strings.
:param str encoder: content transfer encoding, for example ``"base64"``.
