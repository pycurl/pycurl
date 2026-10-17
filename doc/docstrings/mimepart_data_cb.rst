data_cb(datasize, read, seek=None, free=None, userdata=None) -> None

Set callback-based data for this part.

*read* uses the same return conventions as ``READFUNCTION``. *seek* follows
``SEEKFUNCTION`` semantics and should return ``SEEKFUNC_OK``,
``SEEKFUNC_FAIL`` or ``SEEKFUNC_CANTSEEK``. *free* runs when libcurl releases
the part.

``Curl.duphandle()`` shares *userdata* between the handles, so *free* runs
once the last of them has been closed.

Corresponds to `curl_mime_data_cb`_ in libcurl.

:param int datasize: total size of the content, or ``-1`` or ``None`` when it
    is not known in advance.
:param callable read: called as ``read(userdata, max_bytes)``.
:param callable seek: called as ``seek(userdata, offset, origin)``, or ``None``.
:param callable free: called as ``free(userdata)``, or ``None``.
:param userdata: any object, passed back to each of the three callbacks.

.. _curl_mime_data_cb:
    https://curl.se/libcurl/c/curl_mime_data_cb.html
