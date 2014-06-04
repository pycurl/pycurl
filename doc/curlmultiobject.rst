.. _curlmultiobject:

CurlMulti Object
================

.. autoclass:: pycurl.CurlMulti

    CurlMulti objects have the following methods:
    
    .. method:: close() -> None

        .. include:: ../build/docstrings/multi_close.rst

    .. method:: perform() -> tuple of status and the number of active Curl objects

        .. include:: ../build/docstrings/multi_perform.rst

    .. method:: add_handle(Curl object) -> None

        .. include:: ../build/docstrings/multi_add_handle.rst

    .. method:: remove_handle(Curl object) -> None

        .. include:: ../build/docstrings/multi_remove_handle.rst

    .. method:: fdset() -> tuple of lists with active file descriptors, readable, writeable, exceptions

        .. include:: ../build/docstrings/multi_fdset.rst

    .. method:: select([timeout]) -> number of ready file descriptors or -1 on timeout

        .. include:: ../build/docstrings/multi_select.rst

    .. method:: info_read([max_objects]) -> tuple(number of queued messages, a list of successful objects, a list of failed objects)

        .. include:: ../build/docstrings/multi_info_read.rst
