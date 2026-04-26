unassign(sock_fd) -> None

Clears the association in the multi handle for the given socket,
releasing the previously assigned object.

``multi.unassign(sock_fd)`` is equivalent to
:py:meth:`multi.assign(sock_fd, None) <pycurl.CurlMulti.assign>`.
Like ``assign()``, it may be called from inside the ``M_SOCKETFUNCTION``.
