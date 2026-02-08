import socket
import pytest
import time
from typing import Generator

from . import appmanager, localhost, util


def _get_free_port() -> int:
    with socket.socket() as s:
        s.bind((localhost, 0))
        return s.getsockname()[1]


def wait_listening(host: str, port: int, timeout: float = 5.0) -> None:
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


@pytest.fixture(scope="module")
def app(request) -> Generator[str, None, None]:
    port = _get_free_port()
    setup, teardown = appmanager.setup(
        (
            "app",
            port,
        )
    )
    setup(request.module)
    wait_listening(localhost, port, timeout=10.0)
    yield f"http://{localhost}:{port}"
    teardown(request.module)
