import time
import threading

import pytest

import pycurl

from . import util

util.skip_module_without_websockets()


def _run_with_cb(url):
    c = pycurl.Curl()
    chunks = []
    metas = []

    def write_cb(data):
        chunks.append(bytes(data))
        metas.append(c.ws_meta())
        return len(data)

    try:
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.WRITEFUNCTION, write_cb)
        c.perform()
        after = c.ws_meta()
    finally:
        c.close()

    return chunks, metas, after


def _run_with_multi_cb(c, timeout=5.0):
    m = pycurl.CurlMulti()
    errors = []

    try:
        m.add_handle(c)

        deadline = time.monotonic() + timeout
        running = True
        while running:
            _, running = m.perform()
            if running:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AssertionError("timed out waiting for multi ws transfer")
                m.select(min(0.1, remaining))

        while True:
            queued, _, err = m.info_read()
            errors.extend(err)
            if not queued:
                break
    finally:
        # Handle may already be detached if the transfer errored out.
        try:
            m.remove_handle(c)
        except pycurl.error:
            pass
        c.close()
        m.close()

    return errors


def _assert_only_write_error(errors):
    assert errors
    assert all(err_code == pycurl.E_WRITE_ERROR for _, err_code, _ in errors)


@pytest.mark.parametrize(
    "path, expected_payload, expected_flag",
    [
        ("/echo-on-connect", b"hello", pycurl.WS_TEXT),
        ("/binary-on-connect", b"\x01\x02\x03", pycurl.WS_BINARY),
    ],
    ids=["text", "binary"],
)
def test_write_callback_receives_frame(ws_app, path, expected_payload, expected_flag):
    chunks, metas, after = _run_with_cb(ws_app + path)
    assert chunks[0] == expected_payload
    assert isinstance(metas[0], pycurl.WsFrame)
    assert metas[0].flags & expected_flag
    assert after is None  # ws_meta() is callback-context only


def test_fragmented_callback_receive(ws_app):
    chunks, metas, _ = _run_with_cb(ws_app + "/fragmented-on-connect")

    # Drop the trailing close frame.
    data_metas = [
        (c, m) for c, m in zip(chunks, metas) if m and not (m.flags & pycurl.WS_CLOSE)
    ]
    payload = b"".join(c for c, _ in data_metas)
    assert payload == b"one-two-three"

    # Server sends three wire-level fragments; at least one must carry WS_CONT.
    if len(data_metas) > 1:
        assert any(m.flags & pycurl.WS_CONT for _, m in data_metas)


def test_close_frame_visible_in_callback(ws_app):
    _, metas, _ = _run_with_cb(ws_app + "/echo-on-connect")
    assert any(m and (m.flags & pycurl.WS_CLOSE) for m in metas)


def test_raw_mode_callback_receives_wire_bytes(ws_app):
    c = pycurl.Curl()
    chunks = []
    metas = []

    def cb(data):
        chunks.append(bytes(data))
        metas.append(c.ws_meta())
        return len(data)

    try:
        c.setopt(pycurl.URL, ws_app + "/echo-on-connect")
        c.setopt(pycurl.WS_OPTIONS, pycurl.WS_RAW_MODE)
        c.setopt(pycurl.WRITEFUNCTION, cb)
        c.perform()
    finally:
        c.close()

    assert b"".join(chunks) == b"\x81\x05hello\x88\x02\x03\xe8"
    assert metas
    assert all(m is None for m in metas)


def test_ws_meta_none_in_http_callback(app):
    # Non-WebSocket transfer: curl_ws_meta() returns NULL -> None.
    _, metas, _ = _run_with_cb(app + "/success")
    assert metas
    assert all(m is None for m in metas)


def test_write_callback_can_ws_send_reply(ws_app):
    c = pycurl.Curl()
    sent = []

    def cb(data):
        if data == b"hi":
            sent.append(c.ws_send(b"ack", pycurl.WS_BINARY))
        return len(data)

    try:
        c.setopt(pycurl.URL, ws_app + "/greet-and-echo-reply")
        c.setopt(pycurl.WRITEFUNCTION, cb)
        c.perform()
    finally:
        c.close()

    assert sent == [3]


def test_write_callback_can_ws_close(ws_app):
    c = pycurl.Curl()
    closed = []

    def cb(data):
        if data == b"hi":
            closed.append(c.ws_close(1000))
        return len(data)

    try:
        c.setopt(pycurl.URL, ws_app + "/greet-and-wait-close")
        c.setopt(pycurl.WRITEFUNCTION, cb)
        c.perform()
    finally:
        c.close()

    assert closed == [2]  # 2-byte status-code payload


def test_multi_write_callback_receives_frame(ws_app):
    c = pycurl.Curl()
    chunks = []
    metas = []

    def cb(data):
        chunks.append(bytes(data))
        metas.append(c.ws_meta())
        return 0

    c.setopt(pycurl.URL, ws_app + "/echo-on-connect")
    c.setopt(pycurl.WRITEFUNCTION, cb)
    errors = _run_with_multi_cb(c)

    _assert_only_write_error(errors)
    assert chunks[0] == b"hello"
    assert isinstance(metas[0], pycurl.WsFrame)
    assert metas[0].flags & pycurl.WS_TEXT


def test_multi_write_callback_can_ws_send_reply(ws_app):
    c = pycurl.Curl()
    sent = []

    def cb(data):
        if data == b"hi":
            sent.append(c.ws_send(b"ack", pycurl.WS_BINARY))
            return 0
        return len(data)

    c.setopt(pycurl.URL, ws_app + "/greet-and-echo-reply")
    c.setopt(pycurl.WRITEFUNCTION, cb)
    errors = _run_with_multi_cb(c)

    _assert_only_write_error(errors)
    assert sent == [3]


def test_multi_write_callback_can_ws_close(ws_app):
    c = pycurl.Curl()
    closed = []

    def cb(data):
        if data == b"hi":
            closed.append(c.ws_close(1000))
            return 0
        return len(data)

    c.setopt(pycurl.URL, ws_app + "/greet-and-wait-close")
    c.setopt(pycurl.WRITEFUNCTION, cb)
    errors = _run_with_multi_cb(c)

    _assert_only_write_error(errors)
    assert closed == [2]


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.ws_send(b"ack", pycurl.WS_BINARY),
        lambda c: c.ws_close(1000),
    ],
    ids=["ws_send", "ws_close"],
)
def test_write_callback_relaxation_does_not_allow_other_threads(ws_app, call):
    c = pycurl.Curl()
    saw_data = threading.Event()
    release_cb = threading.Event()
    results = []

    def cb(data):
        if data == b"hi":
            saw_data.set()
            release_cb.wait(5.0)
            return 0  # abort the transfer; no need to wait for close handshake
        return len(data)

    def run():
        try:
            c.setopt(pycurl.URL, ws_app + "/greet-and-close")
            c.setopt(pycurl.WRITEFUNCTION, cb)
            c.perform()
            results.append("ok")
        except Exception as e:
            results.append(repr(e))

    t = threading.Thread(target=run)
    t.start()
    assert saw_data.wait(5.0)
    try:
        with pytest.raises(pycurl.error, match="outside WRITEFUNCTION callback"):
            call(c)
    finally:
        release_cb.set()
    t.join(5.0)
    assert not t.is_alive()
    assert len(results) == 1
    c.close()


def test_write_callback_ws_recv_still_rejected(ws_app):
    # Callback-context relaxation is send-only; libcurl doesn't document recv.
    c = pycurl.Curl()
    errors = []

    def cb(data):
        try:
            c.ws_recv(4096)
        except pycurl.error as e:
            errors.append(e)
        return len(data)

    try:
        c.setopt(pycurl.URL, ws_app + "/echo-on-connect")
        c.setopt(pycurl.WRITEFUNCTION, cb)
        c.perform()
    finally:
        c.close()

    assert errors
    assert "perform" in str(errors[0])
