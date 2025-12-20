select([timeout]) -> number of ready file descriptors or 0 on timeout

Returns result from doing a select() on the curl multi file descriptor
with the given timeout.

This is a convenience function which simplifies the combined use of
``fdset()`` and the ``select`` module.

Example usage::

    import pycurl
    c = pycurl.Curl()
    c.setopt(pycurl.URL, "https://curl.haxx.se")
    m = pycurl.CurlMulti()
    m.add_handle(c)
    _, num_handles = m.perform()
    while num_handles:
        ret = m.select(1.0)
        if ret == 0:  continue
        _, num_handles = m.perform()
