unsetopt(option) -> None

Reset curl session option to its default value.

Only some curl options may be reset via this method.

libcurl does not provide a way to reset a single option to its default value;
:py:meth:`pycurl.Curl.reset` resets all options to their default values,
otherwise :py:meth:`pycurl.Curl.setopt` must be called with whatever value
is the default. For convenience, PycURL provides this unsetopt method
to reset some of the options to their default values.

Raises pycurl.error exception on failure.

``c.unsetopt(option)`` is equivalent to ``c.setopt(option, None)``.
