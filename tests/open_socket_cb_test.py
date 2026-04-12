from __future__ import annotations

import socket
from io import BytesIO

import pycurl
import pytest

from . import util


def _make_socket(curl_address):
    family, socktype, protocol, address = curl_address
    s = socket.socket(family, socktype, protocol)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    return s, address


@util.only_unix
def test_socket_open_ipv4(curl, app):
    captured = {}

    def on_open(purpose, curl_address):
        s, addr = _make_socket(curl_address)
        captured["address"] = addr
        return s

    curl.setopt(pycurl.OPENSOCKETFUNCTION, on_open)
    curl.setopt(curl.URL, f"{app}/success")
    sio = BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    curl.perform()

    assert captured["address"] == ("127.0.0.1", pytest.approx(captured["address"][1]))
    assert sio.getvalue().decode() == "success"


@util.only_ipv6
def test_socket_open_ipv6(curl, app):
    captured = {}

    def on_open(purpose, curl_address):
        s, addr = _make_socket(curl_address)
        captured["address"] = addr
        return s

    curl.setopt(pycurl.OPENSOCKETFUNCTION, on_open)
    curl.setopt(curl.URL, f"{app.replace('127.0.0.1', '[::1]')}/success")
    sio = BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    with pytest.raises(pycurl.error):
        # perform fails because we do not listen on ::1
        curl.perform()

    addr = captured["address"]
    assert len(addr) == 4
    assert addr[0] == "::1"
    assert isinstance(addr[2], int)
    assert isinstance(addr[3], int)


@util.min_libcurl(7, 40, 0)
@util.only_unix
def test_socket_open_unix(curl, app):
    captured = {}

    def on_open(purpose, curl_address):
        captured["address"] = curl_address[3]
        sockets = socket.socketpair()
        sockets[0].close()
        return sockets[1]

    curl.setopt(pycurl.OPENSOCKETFUNCTION, on_open)
    curl.setopt(curl.URL, f"{app}/success")
    curl.setopt(curl.UNIX_SOCKET_PATH, "/tmp/pycurl-test-path.sock")
    sio = BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    with pytest.raises(pycurl.error):
        # perform fails because we return a socket not attached to anything
        curl.perform()

    assert isinstance(captured["address"], bytes)
    assert captured["address"] == b"/tmp/pycurl-test-path.sock"


def test_opensocket_set_none(curl):
    curl.setopt(pycurl.OPENSOCKETFUNCTION, None)


def test_opensocket_unset(curl):
    curl.unsetopt(pycurl.OPENSOCKETFUNCTION)


def test_socket_bad_constant():
    assert pycurl.SOCKET_BAD == -1


def test_socket_open_bad(curl, app):
    """Returning SOCKET_BAD should cause a connection error."""
    curl.setopt(pycurl.OPENSOCKETFUNCTION, lambda purpose, addr: pycurl.SOCKET_BAD)
    curl.setopt(curl.URL, f"{app}/success")
    with pytest.raises(pycurl.error) as exc_info:
        curl.perform()

    err_code = exc_info.value.args[0]
    # libcurl 7.38.0 fails with a timeout instead of COULDNT_CONNECT
    assert err_code in (pycurl.E_COULDNT_CONNECT, pycurl.E_OPERATION_TIMEDOUT)


@pytest.mark.parametrize(
    "return_value, desc",
    [
        ("not a socket", "string without fileno"),
        (object(), "plain object without fileno"),
    ],
    ids=["string", "plain-object"],
)
def test_socket_open_no_fileno(curl, app, return_value, desc):
    """Returning an object without fileno should fail with a clear error."""
    curl.setopt(pycurl.OPENSOCKETFUNCTION, lambda purpose, addr: return_value)
    curl.setopt(curl.URL, f"{app}/success")
    with pytest.raises(pycurl.error):
        curl.perform()


def test_socket_open_broken_fileno(curl, app):
    """Returning an object whose fileno property raises should propagate."""

    class BrokenSocket:
        @property
        def fileno(self):
            raise RuntimeError("broken fileno property")

    curl.setopt(pycurl.OPENSOCKETFUNCTION, lambda purpose, addr: BrokenSocket())
    curl.setopt(curl.URL, f"{app}/success")
    with pytest.raises(pycurl.error):
        curl.perform()
