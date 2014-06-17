select([timeout]) -> number of ready file descriptors or -1 on timeout

Returns result from doing a select() on the curl multi file descriptor
with the given timeout.

This is a convenience function which simplifies the combined use of
``fdset()`` and the ``select`` module.

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
        ret = m.select(1.0)
        if ret == -1:  continue
        while 1:
            ret, num_handles = m.perform()
            if ret != pycurl.E_CALL_MULTI_PERFORM: break
