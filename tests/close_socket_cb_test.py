import gc
import socket

import pytest

import pycurl

from . import util

pytestmark = pytest.mark.skipif(
    util.pycurl_version_less_than(7, 21, 7), reason="libcurl < 7.21.7"
)


def _record_and_return(called, value):
    def closesocketfunction(curlfd):
        called.append(True)
        return value

    return closesocketfunction


@pytest.fixture
def closesocket_curl(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    curl.setopt(pycurl.FORBID_REUSE, True)
    return curl


def test_closesocketfunction_ok(closesocket_curl):
    called = []

    def closesocketfunction(curlfd):
        called.append(True)
        socket.fromfd(curlfd, socket.AF_INET, socket.SOCK_STREAM).close()
        return 0

    closesocket_curl.setopt(pycurl.CLOSESOCKETFUNCTION, closesocketfunction)

    closesocket_curl.perform()
    assert called


@pytest.mark.parametrize("return_value", [1, "bogus"], ids=["failure", "bogus"])
def test_closesocketfunction_error_does_not_fail_the_transfer(
    closesocket_curl, return_value
):
    called = []
    closesocket_curl.setopt(
        pycurl.CLOSESOCKETFUNCTION, _record_and_return(called, return_value)
    )

    # libcurl has nowhere to report a failed close, so the transfer still succeeds.
    closesocket_curl.perform()
    assert called


# CONNECT_ONLY keeps the socket open past perform(), so closesocket runs from
# curl_easy_cleanup() instead.
def _connect_only(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    curl.setopt(pycurl.IPRESOLVE, pycurl.IPRESOLVE_V4)
    curl.setopt(pycurl.FORBID_REUSE, False)
    curl.setopt(pycurl.CONNECT_ONLY, True)
    return curl


@pytest.fixture
def connect_only_curl(curl, app):
    return _connect_only(curl, app)


def test_closesocketfunction_on_close(connect_only_curl):
    called = []
    connect_only_curl.setopt(pycurl.CLOSESOCKETFUNCTION, _record_and_return(called, 1))

    assert connect_only_curl.getinfo(pycurl.ACTIVESOCKET) == -1
    connect_only_curl.perform()
    assert connect_only_curl.getinfo(pycurl.ACTIVESOCKET) != -1
    assert not called

    connect_only_curl.close()
    assert called


def test_closesocketfunction_on_dealloc(app):
    called = []

    curl = _connect_only(util.DefaultCurl(), app)
    curl.setopt(pycurl.CLOSESOCKETFUNCTION, _record_and_return(called, 1))

    assert curl.getinfo(pycurl.ACTIVESOCKET) == -1
    curl.perform()
    assert curl.getinfo(pycurl.ACTIVESOCKET) != -1
    assert not called

    del curl
    gc.collect()

    assert called


def test_closesocketfunction_none(curl):
    curl.setopt(pycurl.CLOSESOCKETFUNCTION, None)


def test_closesocketfunction_unset(curl):
    curl.unsetopt(pycurl.CLOSESOCKETFUNCTION)
