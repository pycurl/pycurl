from __future__ import annotations

import socket
import time
from typing import TYPE_CHECKING, Generator
from urllib.parse import urlparse

import pytest

from . import appmanager, localhost, util

if TYPE_CHECKING:
    import pycurl


DEFAULT_WAIT_TIMEOUT = 30.0


def _get_free_port() -> int:
    with socket.socket() as s:
        s.bind((localhost, 0))
        return s.getsockname()[1]


def wait_listening(host: str, port: int, timeout: float = DEFAULT_WAIT_TIMEOUT) -> None:
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            socket.create_connection((host, port), timeout=0.2).close()
            return
        except OSError:
            time.sleep(0.05)

    raise RuntimeError(f"App did not start listening on {host}:{port}")


@pytest.fixture
def free_port() -> int:
    return _get_free_port()


@pytest.fixture
def curl():
    c = util.DefaultCurl()
    yield c
    c.close()


@pytest.fixture(scope="session")
def app() -> Generator[str, None, None]:
    yield from make_app()


@pytest.fixture(scope="session")
def ssl_app() -> Generator[str, None, None]:
    yield from make_app(ssl=True)


@pytest.fixture
def ssl_curl(ssl_app: str) -> Generator[pycurl.Curl, None, None]:
    port = urlparse(ssl_app).port
    assert port is not None
    c = util.DefaultCurlLocalhost(port)
    yield c
    c.close()


def make_app(ssl: bool = False) -> Generator[str, None, None]:
    port = _get_free_port()
    kwargs = {"ssl": True} if ssl else {}
    setup, teardown = appmanager.setup(("app", port, kwargs))

    # appmanager.setup() stores server state on the object passed to setup/teardown.
    # At session scope we don't have a module object, so use a tiny holder.
    class _AppState:
        pass

    state = _AppState()
    setup(state)
    wait_listening(localhost, port, timeout=DEFAULT_WAIT_TIMEOUT)
    # SSL tests need the URL hostname to match the cert SAN (DNS:localhost).
    scheme, host = ("https", "localhost") if ssl else ("http", localhost)
    yield f"{scheme}://{host}:{port}"
    teardown(state)


@pytest.fixture(scope="session")
def ws_app() -> Generator[str, None, None]:
    from . import wsappmanager

    port = _get_free_port()
    server = wsappmanager.start_server(localhost, port)
    wait_listening(localhost, port, timeout=DEFAULT_WAIT_TIMEOUT)
    try:
        yield f"ws://{localhost}:{port}"
    finally:
        server.stop()


@pytest.fixture(scope='session')
def sftp_server():
    from .sftp import LocalSFTPServer
    server = LocalSFTPServer()
    server.start()
    if not util.wait_for_network_service(('127.0.0.1', server.port), 0.1, 20):
        pytest.fail('Local SFTP server did not start in time')
    yield server
    server.stop()


@pytest.fixture(scope='session')
def known_hosts_file(sftp_server, tmp_path_factory):
    import paramiko
    # A mismatched key ensures the keyfunction is always invoked with
    # CURLKHMATCH_MISMATCH, so the callback return value drives test outcomes.
    different_key = paramiko.RSAKey.generate(2048)
    entry = f'[127.0.0.1]:{sftp_server.port} {different_key.get_name()} {different_key.get_base64()}\n'
    path = tmp_path_factory.mktemp('ssh') / 'known_hosts'
    path.write_text(entry)
    return str(path)


@pytest.fixture
def sftp_curl(sftp_server):
    import pycurl
    c = util.DefaultCurl()
    c.setopt(pycurl.URL, f'sftp://127.0.0.1:{sftp_server.port}')
    c.setopt(pycurl.VERBOSE, True)
    yield c
    c.close()
