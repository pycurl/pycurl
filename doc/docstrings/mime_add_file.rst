add_file(name, path, filename=None, content_type=None, headers=None, encoder=None) -> CurlMimePart

Add a file upload part reading from *path* and return it.

Equivalent to ``add(name=name, file=path, ...)``.

:param str name: field name.
:param str path: path to the file to upload. It is opened to check that it
    is readable, and read again by libcurl during the transfer.
:param str filename: remote filename to report. When omitted libcurl
    derives it from *path*.
:param str content_type: value for the part's ``Content-Type`` header.
:param headers: extra headers, as a list or tuple of strings.
:param str encoder: content transfer encoding, for example ``"base64"``.
