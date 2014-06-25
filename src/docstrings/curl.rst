Curl() -> New Curl object

Creates a new :ref:`curlobject` which corresponds to a
``CURL`` handle in libcurl. Curl objects automatically set
CURLOPT_VERBOSE to 0, CURLOPT_NOPROGRESS to 1, provide a default
CURLOPT_USERAGENT and setup CURLOPT_ERRORBUFFER to point to a
private error buffer.

Implicitly calls :py:func:`pycurl.global_init` if the latter has not yet been called.
