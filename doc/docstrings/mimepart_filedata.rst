filedata(path) -> None

Set on-disk file data for this part.

Corresponds to `curl_mime_filedata`_ in libcurl.

:param str path: path to the file to read the content from. A byte string is
    also accepted.

.. _curl_mime_filedata:
    https://curl.se/libcurl/c/curl_mime_filedata.html
