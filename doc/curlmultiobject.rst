CurlMulti Object
================

CurlMulti objects have the following methods:

**close**\ () -> *None*

Corresponds to `curl_multi_cleanup`_ in libcurl. This method is
automatically called by pycurl when a CurlMulti object no longer has any
references to it, but can also be called explicitly.

**perform**\ () -> *tuple of status and the number of active Curl objects*

Corresponds to `curl_multi_perform`_ in libcurl.

**add_handle**\ (*Curl object*)  -> *None*

Corresponds to `curl_multi_add_handle`_ in libcurl. This method adds an
existing and valid Curl object to the CurlMulti object.

IMPORTANT NOTE: add_handle does not implicitly add a Python reference to the
Curl object (and thus does not increase the reference count on the Curl
object).

**remove_handle**\ (*Curl object*) -> *None*

Corresponds to `curl_multi_remove_handle`_ in libcurl. This method
removes an existing and valid Curl object from the CurlMulti object.

IMPORTANT NOTE: remove_handle does not implicitly remove a Python reference
from the Curl object (and thus does not decrease the reference count on the
Curl object).

**fdset**\ () -> *triple of lists with active file descriptors, readable,
writeable, exceptions.*

Corresponds to `curl_multi_fdset`_ in libcurl. This method extracts the
file descriptor information from a CurlMulti object. The returned lists can
be used with the ``select`` module to poll for events.

Example usage:

::

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

**select**\ (*timeout*) -> *number of ready file descriptors or -1 on timeout*

This is a convenience function which simplifies the combined use of
``fdset()`` and the ``select`` module.

Example usage:

::

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

**info_read**\ (*[max]*) -> *number of queued messages, a list of
successful objects, a list of failed objects*

Corresponds to the `curl_multi_info_read`_ function in libcurl. This
method extracts at most *max* messages from the multi stack and returns them
in two lists. The first list contains the handles which completed
successfully and the second list contains a tuple *(curl object, curl error
number, curl error message)* for each failed curl object. The number of
queued messages after this method has been called is also returned.

.. _curl_multi_cleanup:
    http://curl.haxx.se/libcurl/c/curl_multi_cleanup.html
.. _curl_multi_perform:
    http://curl.haxx.se/libcurl/c/curl_multi_perform.html
.. _curl_multi_add_handle:
    http://curl.haxx.se/libcurl/c/curl_multi_add_handle.html
.. _curl_multi_remove_handle:
    http://curl.haxx.se/libcurl/c/curl_multi_remove_handle.html
.. _curl_multi_fdset:
    http://curl.haxx.se/libcurl/c/curl_multi_fdset.html
.. _curl_multi_info_read:
    http://curl.haxx.se/libcurl/c/curl_multi_info_read.html
