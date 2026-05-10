unshare(*data) -> None

Mark one or more data kinds as no longer shared.

Equivalent to calling ``setopt(SH_UNSHARE, item)`` for each *item*. Each *item*
must be one of: ``LOCK_DATA_COOKIE``, ``LOCK_DATA_DNS``,
``LOCK_DATA_SSL_SESSION``, ``LOCK_DATA_CONNECT`` or ``LOCK_DATA_PSL``.

At least one argument is required. Lists and tuples are not expanded — pass
each constant individually. Items are applied sequentially under the
CurlShare object lock; on failure, items already applied are not rolled back.

Example usage::

    import pycurl
    s = pycurl.CurlShare()
    s.share(pycurl.LOCK_DATA_COOKIE, pycurl.LOCK_DATA_DNS)
    s.unshare(pycurl.LOCK_DATA_COOKIE)

Raises pycurl.error exception upon failure.
