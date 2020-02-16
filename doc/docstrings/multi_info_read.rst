info_read([max_objects]) -> tuple(number of queued messages, a list of successful objects, a list of failed objects)

Corresponds to the `curl_multi_info_read`_ function in libcurl.

This method extracts at most *max* messages from the multi stack and returns
them in two lists. The first list contains the handles which completed
successfully and the second list contains a tuple *(curl object, curl error
number, curl error message)* for each failed curl object. The curl error
message is returned as a Python string which is decoded from the curl error
string using the `surrogateescape`_ error handler. The number of
queued messages after this method has been called is also returned.

.. _curl_multi_info_read:
    https://curl.haxx.se/libcurl/c/curl_multi_info_read.html

.. _surrogateescape:
    https://www.python.org/dev/peps/pep-0383/
