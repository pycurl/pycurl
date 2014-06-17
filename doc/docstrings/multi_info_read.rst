info_read([max_objects]) -> tuple(number of queued messages, a list of successful objects, a list of failed objects)

Returns a tuple (number of queued handles, [curl objects]).

Corresponds to the `curl_multi_info_read`_ function in libcurl. This
method extracts at most *max* messages from the multi stack and returns them
in two lists. The first list contains the handles which completed
successfully and the second list contains a tuple *(curl object, curl error
number, curl error message)* for each failed curl object. The number of
queued messages after this method has been called is also returned.

.. _curl_multi_info_read:
    http://curl.haxx.se/libcurl/c/curl_multi_info_read.html
