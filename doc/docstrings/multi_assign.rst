assign(sock_fd, object) -> None

Creates an association in the multi handle between the given socket and
a private object in the application.
Corresponds to `curl_multi_assign`_ in libcurl.
The multi handle keeps a strong reference to the assigned object.

``assign()`` may be called from inside the ``M_SOCKETFUNCTION`` callback;
this is the typical place to attach per-socket state. The new value takes
effect for *future* callbacks for that socket -- the ``socketp`` argument
already passed to the in-flight callback is not mutated.

If ``object`` is ``None``, clears any association for the socket.
For convenience, :py:meth:`pycurl.CurlMulti.unassign` is equivalent to
``multi.assign(sock_fd, None)``.

.. _curl_multi_assign: https://curl.haxx.se/libcurl/c/curl_multi_assign.html
