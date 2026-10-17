add_multipart(name=None, subtype="mixed") -> CurlMime

Add a nested multipart part and return the child ``CurlMime`` attached to
it.

The child is owned by this tree, so it is released with the parent and
cannot be attached anywhere else or set as ``MIMEPOST``.

:param str name: part name.
:param str subtype: multipart subtype, giving a ``Content-Type`` of
    ``multipart/<subtype>``. Pass ``None`` to leave the type unset.
