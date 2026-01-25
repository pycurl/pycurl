import socket
import time
from typing import Generator

import pytest

import pycurl

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


POST_OPTS = [pycurl.HTTPPOST]
POST_OPT_IDS = {
    pycurl.HTTPPOST: "httppost",
}
if not util.pycurl_version_less_than(7, 56, 0):
    POST_OPTS.append(pycurl.MIMEPOST)
    POST_OPT_IDS[pycurl.MIMEPOST] = "mimepost"


def post_opt_id(opt):
    return POST_OPT_IDS.get(opt, str(opt))


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
    port = _get_free_port()
    setup, teardown = appmanager.setup(
        (
            "app",
            port,
        )
    )

    # appmanager.setup() stores server state on the object passed to setup/teardown.
    # At session scope we don't have a module object, so use a tiny holder.
    class _AppState:
        pass

    state = _AppState()
    setup(state)
    wait_listening(localhost, port, timeout=10.0)
    yield f"http://{localhost}:{port}"
    teardown(state)


@pytest.fixture(params=POST_OPTS, ids=post_opt_id)
def post_opt(request):
    return request.param
