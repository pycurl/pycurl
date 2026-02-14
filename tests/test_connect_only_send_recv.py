import errno
import select
import time
from urllib.parse import urlparse

import numpy as np
import pycurl
import pytest

IO_TIMEOUT = 5.0
POLL_INTERVAL = 0.01


def _connect_only(curl, app):
    curl.setopt(pycurl.FORBID_REUSE, False)
    curl.setopt(pycurl.URL, f"{app}/success")
    curl.setopt(pycurl.CONNECT_ONLY, True)
    curl.perform()


@pytest.fixture
def connected_curl(curl, app):
    _connect_only(curl, app)
    return curl


@pytest.fixture
def success_request(app):
    host = urlparse(app).netloc
    return (
        f"GET /success HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    ).encode("ascii")


def _assert_success_response(response):
    assert b"200 OK" in response
    assert b"\r\n\r\nsuccess" in response


def _as_numpy_uint8(payload):
    return np.frombuffer(payload, dtype=np.uint8)


def _send_all(curl, payload):
    view = memoryview(payload)
    total = 0
    deadline = time.monotonic() + IO_TIMEOUT

    while total < len(view):
        if time.monotonic() > deadline:
            raise AssertionError("timed out while sending request")
        try:
            sent = curl.send(view[total:])
        except BlockingIOError as exc:
            assert exc.errno == errno.EAGAIN
            time.sleep(POLL_INTERVAL)
            continue
        assert sent > 0
        total += sent


def _recv_all(curl):
    chunks = []
    deadline = time.monotonic() + IO_TIMEOUT

    while True:
        if time.monotonic() > deadline:
            raise AssertionError("timed out while reading response")
        try:
            data = curl.recv(4096)
        except BlockingIOError as exc:
            assert exc.errno == errno.EAGAIN
            time.sleep(POLL_INTERVAL)
            continue
        if not data:
            break
        chunks.append(data)

    return b"".join(chunks)


def _recv_all_into(curl, buf):
    out = bytearray()
    deadline = time.monotonic() + IO_TIMEOUT
    while True:
        if time.monotonic() > deadline:
            raise AssertionError("timed out while reading response via recv_into")
        try:
            nread = curl.recv_into(buf)
        except BlockingIOError as exc:
            assert exc.errno == errno.EAGAIN
            time.sleep(POLL_INTERVAL)
            continue
        if nread == 0:
            break
        out.extend(memoryview(buf)[:nread])
    return bytes(out)


def _recv_into_once(curl, buffer, nbytes):
    deadline = time.monotonic() + IO_TIMEOUT
    while True:
        if time.monotonic() > deadline:
            raise AssertionError("timed out while waiting for recv_into data")
        try:
            return curl.recv_into(buffer, nbytes)
        except BlockingIOError as exc:
            assert exc.errno == errno.EAGAIN
            time.sleep(POLL_INTERVAL)


def _wait_active_socket(curl, *, for_read=False, for_write=False):
    assert for_read or for_write
    socket_info = (
        pycurl.ACTIVESOCKET if hasattr(pycurl, "ACTIVESOCKET") else pycurl.LASTSOCKET
    )
    socket_fd = curl.getinfo(socket_info)
    assert socket_fd != -1

    deadline = time.monotonic() + IO_TIMEOUT
    while True:
        timeout = deadline - time.monotonic()
        if timeout <= 0:
            mode = "readable" if for_read else "writable"
            raise AssertionError(
                f"timed out waiting for active socket to become {mode}"
            )

        readable, writable, _ = select.select(
            [socket_fd] if for_read else [],
            [socket_fd] if for_write else [],
            [],
            timeout,
        )
        if (for_read and readable) or (for_write and writable):
            return


def test_connect_only_recv_would_block_before_request(connected_curl):
    with pytest.raises(BlockingIOError) as excinfo:
        connected_curl.recv(16)
    assert excinfo.value.errno == errno.EAGAIN


@pytest.mark.parametrize(
    "make_payload", (bytes, bytearray, memoryview, _as_numpy_uint8)
)
def test_connect_only_send_recv_byteslike(
    connected_curl, success_request, make_payload
):
    _send_all(connected_curl, make_payload(success_request))
    response = _recv_all(connected_curl)
    _assert_success_response(response)


def test_connect_only_recv_into(connected_curl, success_request):
    _send_all(connected_curl, success_request)
    response = _recv_all_into(connected_curl, bytearray(128))
    _assert_success_response(response)


def test_connect_only_recv_into_numpy_array(connected_curl, success_request):
    _send_all(connected_curl, success_request)
    response = _recv_all_into(connected_curl, np.empty(128, dtype=np.uint8))
    _assert_success_response(response)


def test_connect_only_recv_into_would_block_before_request(connected_curl):
    buf = bytearray(16)
    with pytest.raises(BlockingIOError) as excinfo:
        connected_curl.recv_into(buf)
    assert excinfo.value.errno == errno.EAGAIN


def test_connect_only_recv_into_respects_nbytes(connected_curl, success_request):
    _send_all(connected_curl, success_request)
    buf = bytearray(8)
    nread = _recv_into_once(connected_curl, buf, 1)
    assert nread == 1


def test_connect_only_waits_for_activity_on_active_socket(
    connected_curl, success_request
):
    socket_info = (
        pycurl.ACTIVESOCKET if hasattr(pycurl, "ACTIVESOCKET") else pycurl.LASTSOCKET
    )
    socket_fd = connected_curl.getinfo(socket_info)
    assert socket_fd != -1
    if hasattr(pycurl, "ACTIVESOCKET") and hasattr(pycurl, "LASTSOCKET"):
        assert socket_fd == connected_curl.getinfo(pycurl.LASTSOCKET)

    _wait_active_socket(connected_curl, for_write=True)
    _send_all(connected_curl, success_request)

    _wait_active_socket(connected_curl, for_read=True)
    response = _recv_all(connected_curl)
    _assert_success_response(response)


def test_recv_into_validates_nbytes(curl):
    buf = bytearray(8)

    with pytest.raises(ValueError, match="negative buffersize in recv_into"):
        curl.recv_into(buf, -1)

    with pytest.raises(ValueError, match="buffer too small for requested bytes"):
        curl.recv_into(buf, 9)


def test_recv_validates_size(curl):
    with pytest.raises(ValueError, match="negative buffersize in recv"):
        curl.recv(-1)


def test_recv_zero_size_returns_empty_bytes(curl):
    assert curl.recv(0) == b""


def test_recv_into_requires_writable_buffer(curl):
    with pytest.raises(TypeError):
        curl.recv_into(memoryview(b"immutable"))


def test_recv_into_zero_length_buffer_returns_zero(curl):
    assert curl.recv_into(bytearray(), 0) == 0


def test_send_requires_bytes_like(curl):
    with pytest.raises(TypeError):
        curl.send("not-bytes")


@pytest.mark.parametrize(
    ("method_name", "args"),
    (
        ("send", (b"x",)),
        ("recv", (1,)),
        ("recv_into", (bytearray(1),)),
    ),
)
def test_connect_only_methods_require_connect_only(curl, method_name, args):
    with pytest.raises(pycurl.error) as excinfo:
        getattr(curl, method_name)(*args)

    assert excinfo.value.args[0] == pycurl.E_UNSUPPORTED_PROTOCOL
    assert "CONNECT_ONLY is required" in excinfo.value.args[1]
