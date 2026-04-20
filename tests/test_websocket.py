import errno
import select
import time

import pytest

import pycurl

from . import util

util.skip_module_without_websockets()


@pytest.fixture
def wscurl():
    # Plain Curl; DefaultCurl sets FORBID_REUSE which breaks CONNECT_ONLY=2.
    c = pycurl.Curl()
    yield c
    c.close()


@pytest.fixture
def connected(wscurl, ws_app):
    wscurl.setopt(pycurl.URL, ws_app + "/echo")
    wscurl.setopt(pycurl.CONNECT_ONLY, 2)
    wscurl.perform()
    return wscurl


def _wait_readable(c, timeout):
    fd = c.getinfo(pycurl.ACTIVESOCKET)
    r, _, _ = select.select([fd], [], [], timeout)
    return bool(r)


def _recv(c, bufsize, timeout=5.0):
    # Try ws_recv() first (libcurl may hold buffered data); fall back to
    # select() on BlockingIOError / CURLE_AGAIN.
    deadline = time.monotonic() + timeout
    while True:
        try:
            return c.ws_recv(bufsize)
        except BlockingIOError:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError("timed out waiting for ws data")
            _wait_readable(c, remaining)


def _recv_into(c, buffer, nbytes=0, timeout=5.0):
    deadline = time.monotonic() + timeout
    while True:
        try:
            return c.ws_recv_into(buffer, nbytes)
        except BlockingIOError:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError("timed out waiting for ws data")
            _wait_readable(c, remaining)


def _recv_until(c, predicate, timeout=5.0):
    # Drain frames until predicate(data, meta) matches. Used by auto-pong tests.
    deadline = time.monotonic() + timeout
    frames = []
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError("timed out waiting for ws data")
        data, meta = _recv(c, 4096, remaining)
        frames.append((data, meta))
        if predicate(data, meta):
            return frames


@pytest.mark.parametrize(
    "name",
    [
        "WS_TEXT",
        "WS_BINARY",
        "WS_CONT",
        "WS_CLOSE",
        "WS_PING",
        "WS_PONG",
        "WS_OFFSET",
        "WS_OPTIONS",
        "WS_RAW_MODE",
        "WsFrame",
    ],
)
def test_constant_present(name):
    assert hasattr(pycurl, name), name


def test_ws_frame_has_expected_fields():
    f = pycurl.WsFrame(1, 2, 3, 4, 5)
    assert (f.age, f.flags, f.offset, f.bytesleft, f.len) == (1, 2, 3, 4, 5)


@pytest.mark.parametrize(
    "payload, flag",
    [
        (b"hello", pycurl.WS_TEXT),
        (bytes(range(32)), pycurl.WS_BINARY),
    ],
    ids=["text", "binary"],
)
def test_roundtrip(connected, payload, flag):
    assert connected.ws_send(payload, flag) == len(payload)
    data, meta = _recv(connected, 4096)
    assert data == payload
    assert meta.flags & flag
    assert meta.bytesleft == 0


def test_recv_into_bytearray(connected):
    connected.ws_send(b"abcdef", pycurl.WS_TEXT)
    buf = bytearray(4096)
    n, meta = _recv_into(connected, buf)
    assert bytes(buf[:n]) == b"abcdef"
    assert meta.flags & pycurl.WS_TEXT


def test_recv_into_memoryview_slice(connected):
    connected.ws_send(b"slicepayload", pycurl.WS_BINARY)
    backing = bytearray(256)
    view = memoryview(backing)[64:128]
    n, meta = _recv_into(connected, view)
    assert n == len(b"slicepayload")
    assert bytes(backing[64 : 64 + n]) == b"slicepayload"
    # Bytes outside the slice must be untouched.
    assert backing[:64] == bytes(64)
    assert backing[128:] == bytes(128)
    assert meta.flags & pycurl.WS_BINARY


@pytest.mark.parametrize(
    "call, exc",
    [
        (lambda c: c.ws_recv(-1), ValueError),
        (lambda c: c.ws_recv_into(bytearray(8), -1), ValueError),
        (lambda c: c.ws_recv_into(bytearray(8), 9999), ValueError),
        (lambda c: c.ws_send(b"x", -1), ValueError),
        (lambda c: c.ws_send(b"x", 1 << 40), OverflowError),
        (lambda c: c.ws_send(b"x", pycurl.WS_BINARY, -1), ValueError),
        (lambda c: c.ws_send(12345), TypeError),
    ],
    ids=[
        "recv_neg_bufsize",
        "recv_into_neg_nbytes",
        "recv_into_nbytes_too_large",
        "send_neg_flags",
        "send_overflow_flags",
        "send_neg_fragsize",
        "send_wrong_data_type",
    ],
)
def test_argument_validation(wscurl, call, exc):
    with pytest.raises(exc):
        call(wscurl)


def test_recv_zero_bufsize(connected):
    connected.ws_send(b"hello", pycurl.WS_TEXT)
    data, meta = _recv(connected, 0)
    assert data == b""
    assert isinstance(meta, pycurl.WsFrame)
    assert meta.flags & pycurl.WS_TEXT
    data, meta = _recv(connected, 4096)
    assert data == b"hello"
    assert meta.flags & pycurl.WS_TEXT


def test_recv_into_empty_buffer(connected):
    connected.ws_send(b"hello", pycurl.WS_TEXT)
    n, meta = _recv_into(connected, bytearray(0))
    assert n == 0
    assert isinstance(meta, pycurl.WsFrame)
    assert meta.flags & pycurl.WS_TEXT
    data, meta = _recv(connected, 4096)
    assert data == b"hello"
    assert meta.flags & pycurl.WS_TEXT


def test_ws_meta_returns_none_outside_callback(wscurl, ws_app):
    assert wscurl.ws_meta() is None  # before perform
    wscurl.setopt(pycurl.URL, ws_app + "/echo")
    wscurl.setopt(pycurl.CONNECT_ONLY, 2)
    wscurl.perform()
    assert wscurl.ws_meta() is None  # detached mode, no callback running


def test_send_on_closed_handle_raises():
    c = pycurl.Curl()
    c.close()
    with pytest.raises(pycurl.error):
        c.ws_send(b"x")


@pytest.mark.parametrize(
    "data, expected_flag, expected_bytes",
    [
        ("hello", pycurl.WS_TEXT, b"hello"),
        ("héllo", pycurl.WS_TEXT, "héllo".encode("utf-8")),
        (b"\x00\xff\x10", pycurl.WS_BINARY, b"\x00\xff\x10"),
        (bytearray(b"abc"), pycurl.WS_BINARY, b"abc"),
        (memoryview(b"mview"), pycurl.WS_BINARY, b"mview"),
    ],
    ids=["str", "str-utf8", "bytes", "bytearray", "memoryview"],
)
def test_send_infers_frame_type(connected, data, expected_flag, expected_bytes):
    connected.ws_send(data)
    received, meta = _recv(connected, 4096)
    assert received == expected_bytes
    assert meta.flags & expected_flag


def test_send_str_custom_encoding(connected):
    # ASCII content avoids the RFC 6455 UTF-8 wire requirement; the
    # non-encodable test proves the encoding kwarg is honored.
    connected.ws_send("hello", encoding="ascii")
    data, meta = _recv(connected, 4096)
    assert data == b"hello"
    assert meta.flags & pycurl.WS_TEXT


def test_send_str_encoding_rejects_non_encodable(connected):
    with pytest.raises(UnicodeEncodeError):
        connected.ws_send("héllo", encoding="ascii")


def test_send_bytes_with_explicit_text_flag(connected):
    # Explicit WS_TEXT overrides the bytes-like inference to WS_BINARY.
    connected.ws_send(b"explicit", pycurl.WS_TEXT)
    data, meta = _recv(connected, 4096)
    assert data == b"explicit"
    assert meta.flags & pycurl.WS_TEXT


@pytest.mark.parametrize(
    "flag, match",
    [(pycurl.WS_BINARY, "WS_BINARY"), (pycurl.WS_CLOSE, "WS_CLOSE")],
    ids=["WS_BINARY", "WS_CLOSE"],
)
def test_send_str_with_incompatible_flag_raises(connected, flag, match):
    with pytest.raises(TypeError, match=match):
        connected.ws_send("nope", flag)


def test_send_rejects_none_data(wscurl):
    with pytest.raises(TypeError, match="NoneType"):
        wscurl.ws_send(None)


def test_send_conflicting_text_binary_flags_raises(wscurl):
    with pytest.raises(ValueError, match="WS_TEXT and WS_BINARY"):
        wscurl.ws_send(b"x", pycurl.WS_TEXT | pycurl.WS_BINARY)


@pytest.mark.parametrize(
    "data, flag",
    [
        ("hello", pycurl.WS_PING),
        ("hello", pycurl.WS_PONG),
        (b"probe", pycurl.WS_PING),
    ],
    ids=["str+WS_PING", "str+WS_PONG", "bytes+WS_PING"],
)
def test_send_control_frame(connected, data, flag):
    connected.ws_send(data, flag)


@pytest.mark.parametrize(
    "flags",
    [
        pycurl.WS_PING | pycurl.WS_CONT,
        pycurl.WS_PONG | pycurl.WS_CONT,
        pycurl.WS_CLOSE | pycurl.WS_CONT,
    ],
    ids=["PING+CONT", "PONG+CONT", "CLOSE+CONT"],
)
def test_send_rejects_fragmented_control_frame(wscurl, flags):
    # RFC 6455 §5.4: control frames MUST NOT be fragmented.
    with pytest.raises(ValueError, match="control frames cannot be fragmented"):
        wscurl.ws_send(b"x", flags)


@pytest.mark.parametrize(
    "flags",
    [
        pycurl.WS_PING | pycurl.WS_PONG,
        pycurl.WS_PING | pycurl.WS_CLOSE,
        pycurl.WS_PONG | pycurl.WS_CLOSE,
        pycurl.WS_PING | pycurl.WS_PONG | pycurl.WS_CLOSE,
    ],
    ids=["PING+PONG", "PING+CLOSE", "PONG+CLOSE", "PING+PONG+CLOSE"],
)
def test_send_rejects_multiple_control_bits(wscurl, flags):
    with pytest.raises(ValueError, match="only one of WS_PING"):
        wscurl.ws_send(b"x", flags)


def test_ws_close_empty(connected):
    assert connected.ws_close() == 0


@pytest.mark.parametrize(
    "code, reason, encoding, expected",
    [
        (1000, None, "utf-8", b"\x03\xe8"),
        (1001, "going away", "utf-8", b"\x03\xe9going away"),
        (1011, b"internal error", "utf-8", b"\x03\xf3internal error"),
        (1000, "héllo", "utf-8", b"\x03\xe8" + "héllo".encode("utf-8")),
        (1000, "hello", "ascii", b"\x03\xe8hello"),
    ],
    ids=["code-only", "str-reason", "bytes-reason", "str-utf8", "ascii-encoding"],
)
def test_ws_close_payload(connected, code, reason, encoding, expected):
    connected.ws_close(code, reason, encoding=encoding)
    data, meta = _recv(connected, 4096)
    assert data == expected
    assert meta.flags & pycurl.WS_CLOSE


@pytest.mark.parametrize("code", [0, 999, 1004, 1005, 1006, 1015, 2000, 5000, -1])
def test_ws_close_code_out_of_range_raises(wscurl, code):
    with pytest.raises(ValueError, match="valid wire close status code"):
        wscurl.ws_close(code)


def test_ws_close_reason_without_code_raises(wscurl):
    with pytest.raises(ValueError, match="reason requires code"):
        wscurl.ws_close(reason="nope")


def test_ws_close_reason_too_long_raises(wscurl):
    # 2-byte code + 124-byte reason = 126, over the 125-byte control-frame cap.
    with pytest.raises(ValueError, match="payload too large"):
        wscurl.ws_close(1000, b"x" * 124)


def test_ws_close_reason_exactly_125_bytes(connected):
    # 2 + 123 = 125, right at the RFC 6455 §5.5 boundary.
    reason = b"y" * 123
    connected.ws_close(1000, reason)
    data, _ = _recv(connected, 4096)
    assert data == b"\x03\xe8" + reason


@pytest.mark.parametrize(
    "reason, encoding, exc",
    [
        ("héllo", "ascii", UnicodeEncodeError),
        (b"\xff", "utf-8", UnicodeDecodeError),
        ("héllo", "latin-1", UnicodeDecodeError),
    ],
    ids=["str-not-encodable", "bytes-not-utf8", "encoded-not-utf8"],
)
def test_ws_close_reason_encoding_errors(wscurl, reason, encoding, exc):
    with pytest.raises(exc):
        wscurl.ws_close(1000, reason, encoding=encoding)


def test_send_fragsize_equal_to_payload(connected):
    # One frame, total size announced up front; pins the fragsize
    # parameter without the multi-call WS_OFFSET dance.
    payload = b"A" * 20
    connected.ws_send(payload, pycurl.WS_BINARY, fragsize=len(payload))
    data, meta = _recv(connected, 4096)
    assert data == payload
    assert meta.flags & pycurl.WS_BINARY


def test_recv_raises_blocking_io_error_when_no_data(wscurl, ws_app):
    # /silent never replies; ws_recv returns CURLE_AGAIN -> BlockingIOError.
    wscurl.setopt(pycurl.URL, ws_app + "/silent")
    wscurl.setopt(pycurl.CONNECT_ONLY, 2)
    wscurl.perform()
    with pytest.raises(BlockingIOError) as exc_info:
        wscurl.ws_recv(4096)
    assert exc_info.value.errno == errno.EAGAIN


def test_default_mode_autopongs_server_ping(wscurl, ws_app):
    wscurl.setopt(pycurl.URL, ws_app + "/ping-and-report-pong")
    wscurl.setopt(pycurl.CONNECT_ONLY, 2)
    wscurl.perform()

    _recv_until(
        wscurl,
        lambda data, meta: (meta.flags & pycurl.WS_TEXT) and data == b"pong-ok",
    )


@pytest.mark.skipif(
    not hasattr(pycurl, "WS_NOAUTOPONG"),
    reason="libcurl < 8.14.0",
)
def test_ws_noautopong_disables_automatic_pong(wscurl, ws_app):
    wscurl.setopt(pycurl.URL, ws_app + "/ping-and-report-pong")
    wscurl.setopt(pycurl.CONNECT_ONLY, 2)
    wscurl.setopt(pycurl.WS_OPTIONS, pycurl.WS_NOAUTOPONG)
    wscurl.perform()

    frames = _recv_until(
        wscurl,
        lambda data, meta: (meta.flags & pycurl.WS_TEXT) and data == b"pong-missing",
    )

    # Server's ping must have reached the client (otherwise auto-pong
    # wasn't disabled — the "pong-missing" signal alone doesn't prove it).
    assert any(meta.flags & pycurl.WS_PING for _, meta in frames)


@pytest.mark.skipif(
    not hasattr(pycurl, "WS_NOAUTOPONG"),
    reason="libcurl < 8.14.0",
)
def test_ws_noautopong_allows_manual_pong(wscurl, ws_app):
    wscurl.setopt(pycurl.URL, ws_app + "/ping-and-report-pong")
    wscurl.setopt(pycurl.CONNECT_ONLY, 2)
    wscurl.setopt(pycurl.WS_OPTIONS, pycurl.WS_NOAUTOPONG)
    wscurl.perform()

    data, meta = _recv(wscurl, 4096)
    assert data == b"probe"
    assert meta.flags & pycurl.WS_PING

    assert wscurl.ws_send(data, pycurl.WS_PONG) == len(data)

    _recv_until(
        wscurl,
        lambda chunk, frame: (frame.flags & pycurl.WS_TEXT) and chunk == b"pong-ok",
    )
