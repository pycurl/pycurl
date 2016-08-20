setopt_string(option, value) -> None

Set curl session option to a string value.

This method allows setting string options that are not officially supported
by PycURL, for example because they did not exist when the version of PycURL
being used was released.
:py:meth:`pycurl.Curl.setopt` should be used for setting options that
PycURL knows about.

**Warning:** No checking is performed that *option* does, in fact,
expect a string value. Using this method incorrectly can crash the program
and may lead to a security vulnerability.
Furthermore, it is on the application to ensure that the *value* object
does not get garbage collected while libcurl is using it.
libcurl copies most string options but not all; one option whose value
is not copied by libcurl is `CURLOPT_POSTFIELDS`_.

*option* would generally need to be given as an integer literal rather than
a symbolic constant.

*value* can be a binary string or a Unicode string using ASCII code points,
same as with string options given to PycURL elsewhere.

Example setting URL via ``setopt_string``::

    import pycurl
    c = pycurl.Curl()
    c.setopt_string(10002, "http://www.python.org/")

.. _CURLOPT_POSTFIELDS: https://curl.haxx.se/libcurl/c/CURLOPT_POSTFIELDS.html
