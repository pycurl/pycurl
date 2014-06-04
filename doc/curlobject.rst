.. _curlobject:

Curl Object
===========

.. autoclass:: pycurl.Curl

    Curl objects have the following methods:

    .. method:: close() -> None
    
        .. include:: ../build/docstrings/curl_close.rst

    .. method:: perform() -> None

        .. include:: ../build/docstrings/curl_perform.rst

    .. method:: reset() -> None

        .. include:: ../build/docstrings/curl_reset.rst

    .. method:: setopt(option, value) -> None

        .. include:: ../build/docstrings/curl_setopt.rst

    .. method:: getinfo(option) -> Result

        .. include:: ../build/docstrings/curl_getinfo.rst

    .. method:: pause(bitmask) -> None

        .. include:: ../build/docstrings/curl_pause.rst

    .. method:: errstr() -> string

        .. include:: ../build/docstrings/curl_errstr.rst
