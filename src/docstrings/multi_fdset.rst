fdset() -> tuple of lists with active file descriptors, readable, writeable, exceptions

Returns a tuple of three lists that can be passed to the select.select() method.

Corresponds to `curl_multi_fdset`_ in libcurl. This method extracts the
file descriptor information from a CurlMulti object. The returned lists can
be used with the ``select`` module to poll for events.

Example usage::

    import pycurl
    c = pycurl.Curl()
    c.setopt(pycurl.URL, "http://curl.haxx.se")
    m = pycurl.CurlMulti()
    m.add_handle(c)
    while 1:
        ret, num_handles = m.perform()
        if ret != pycurl.E_CALL_MULTI_PERFORM: break
    while num_handles:
        apply(select.select, m.fdset() + (1,))
        while 1:
            ret, num_handles = m.perform()
            if ret != pycurl.E_CALL_MULTI_PERFORM: break

.. _curl_multi_fdset:
    http://curl.haxx.se/libcurl/c/curl_multi_fdset.html
