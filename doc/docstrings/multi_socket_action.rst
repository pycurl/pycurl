socket_action(sock_fd, ev_bitmask) -> (result, num_running_handles)

Returns result from doing a socket_action() on the curl multi file descriptor
with the given timeout.
Corresponds to `curl_multi_socket_action`_ in libcurl.

The return value is a two-element tuple. The first element is the return
value of the underlying ``curl_multi_socket_action`` function, and it is
always zero (``CURLE_OK``) because any other return value would cause
``socket_action`` to raise an exception. The second element is the number of
running easy handles within this multi handle. When the number of running
handles reaches zero, all transfers have completed. Note that if the number
of running handles has decreased by one compared to the previous invocation,
this is not mean the handle corresponding to the ``sock_fd`` provided as
the argument to this function was the completed handle.

.. _curl_multi_socket_action: https://curl.haxx.se/libcurl/c/curl_multi_socket_action.html
