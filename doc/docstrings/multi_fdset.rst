fdset() -> tuple of lists with active file descriptors, readable, writeable, exceptions

Returns a tuple of three lists that can be passed to the select.select() method.

Corresponds to `curl_multi_fdset`_ in libcurl. This method extracts the
file descriptor information from a CurlMulti object. The returned lists can
be used with the ``select`` module to poll for events.

Example usage::

    import pycurl
    c = pycurl.Curl()
    c.setopt(pycurl.URL, "https://curl.haxx.se")
    m = pycurl.CurlMulti()
    m.add_handle(c)
    _, num_handles = m.perform()
    while num_handles:
        apply(select.select, m.fdset() + (1,))
        _, num_handles = m.perform()
.. _curl_multi_fdset:
    https://curl.haxx.se/libcurl/c/curl_multi_fdset.html
