from io import BytesIO

import pycurl
import pytest

from . import util


def _configure(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    curl.setopt(pycurl.WRITEFUNCTION, BytesIO().write)


@util.min_libcurl(7, 59, 0)
def test_resolver_start_callback_fires(app, curl):
    calls = []

    def cb():
        calls.append(True)
        return 0

    _configure(curl, app)
    curl.setopt(pycurl.RESOLVER_START_FUNCTION, cb)
    curl.perform()

    assert calls  # called at least once


@util.min_libcurl(7, 59, 0)
def test_resolver_start_callback_abort(app, curl):
    _configure(curl, app)
    curl.setopt(pycurl.RESOLVER_START_FUNCTION, lambda: 1)
    with pytest.raises(pycurl.error):
        curl.perform()


@util.min_libcurl(7, 59, 0)
def test_resolver_start_callback_unset(app, curl):
    _configure(curl, app)
    curl.setopt(pycurl.RESOLVER_START_FUNCTION, lambda: 0)
    curl.unsetopt(pycurl.RESOLVER_START_FUNCTION)
    curl.perform()


@util.min_libcurl(7, 59, 0)
def test_resolver_start_callback_exception_aborts(app, curl):
    def cb():
        raise RuntimeError("boom")

    _configure(curl, app)
    curl.setopt(pycurl.RESOLVER_START_FUNCTION, cb)
    with pytest.raises(pycurl.error):
        curl.perform()
