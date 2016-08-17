socket_action(sockfd, ev_bitmask) -> tuple

Returns result from doing a socket_action() on the curl multi file descriptor
with the given timeout.
Corresponds to `curl_multi_socket_action`_ in libcurl.

.. _curl_multi_socket_action: https://curl.haxx.se/libcurl/c/curl_multi_socket_action.html
