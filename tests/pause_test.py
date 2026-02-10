#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et
import json
import time

import pycurl
import pytest

from . import util

SELECT_TIMEOUT = 0.2


def _pause_state(**extra):
    state = {"paused": False, "resumed": False, "paused_at": None, "unpaused_at": None}
    state.update(extra)
    return state


def _pause_now(state):
    state["paused"] = True
    state["paused_at"] = time.monotonic()


def _pause_on_first_write(curl, state, sink, mask=pycurl.PAUSE_ALL):
    def writefunc(data):
        rv = sink.write(data)
        if not state["paused"]:
            _pause_now(state)
            curl.pause(mask)
        return rv

    return writefunc


def _configure_unpause(curl, state, resume_after, *, use_pause_cont=False):
    def progress(dltotal, dlnow, ultotal, ulnow):
        if state["paused"] and not state["resumed"]:
            if time.monotonic() - state["paused_at"] >= resume_after:
                state["resumed"] = True
                state["unpaused_at"] = time.monotonic()
                if use_pause_cont:
                    curl.pause(pycurl.PAUSE_CONT)
                else:
                    curl.unpause()
        return 0

    curl.setopt(pycurl.NOPROGRESS, False)
    curl.setopt(pycurl.PROGRESSFUNCTION, progress)


def _drive(curl, timeout):
    multi = pycurl.CurlMulti()
    multi.add_handle(curl)
    start = time.monotonic()
    err_list = []

    def drain():
        while True:
            queued, _, err = multi.info_read()
            if err:
                err_list.extend(err)
            if not queued:
                break

    try:
        _, num_handles = multi.perform()
        while num_handles:
            multi.select(SELECT_TIMEOUT)
            if time.monotonic() - start > timeout:
                raise AssertionError("Transfer timed out")
            _, num_handles = multi.perform()
            drain()
        drain()
        return time.monotonic(), err_list
    finally:
        try:
            multi.remove_handle(curl)
        except Exception:
            pass
        multi.close()


def _run_with_unpause_multi(curl, state, resume_after, timeout):
    _configure_unpause(curl, state, resume_after)
    done_at, err_list = _drive(curl, timeout=timeout)
    return done_at, err_list


def _run_with_unpause_easy(curl, state, resume_after, timeout, *, use_pause_cont=False):
    _configure_unpause(curl, state, resume_after, use_pause_cont=use_pause_cont)
    curl.setopt(pycurl.TIMEOUT, int(timeout) + 1)
    err_list = []
    try:
        curl.perform()
    except pycurl.error as exc:
        err_code = exc.args[0] if exc.args else None
        err_msg = exc.args[1] if len(exc.args) > 1 else str(exc)
        err_list.append((curl, err_code, err_msg))
    return time.monotonic(), err_list


def _run_download_pause(
    app, curl, run_with_unpause, *, mask=pycurl.PAUSE_ALL, resume_after=0.7, timeout=4.0
):
    curl.setopt(pycurl.URL, f"{app}/pause")
    sio = util.BytesIO()
    state = _pause_state()
    curl.setopt(
        pycurl.WRITEFUNCTION, _pause_on_first_write(curl, state, sio, mask=mask)
    )
    start = time.monotonic()
    done_at, err_list = run_with_unpause(curl, state, resume_after, timeout)
    return start, done_at, err_list, sio, state


def _run_upload_pause(
    app,
    curl,
    run_with_unpause,
    *,
    mask=pycurl.PAUSE_SEND,
    resume_after=0.2,
    timeout=6.0,
):
    data = b"a" * 16384
    state = _pause_state(offset=0, read_calls=0)

    def readfunc(size):
        state["read_calls"] += 1
        if not state["paused"]:
            _pause_now(state)
            curl.pause(mask)
        if state["offset"] < len(data):
            take = min(size, 1024)
            chunk = data[state["offset"] : state["offset"] + take]
            state["offset"] += len(chunk)
            return chunk
        return b""

    curl.setopt(pycurl.URL, f"{app}/raw_utf8")
    curl.setopt(pycurl.POST, 1)
    curl.setopt(pycurl.HTTPHEADER, ["Content-Type: application/octet-stream"])
    curl.setopt(pycurl.POSTFIELDSIZE, len(data))
    curl.setopt(pycurl.READFUNCTION, readfunc)

    sio = util.BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)

    _, err_list = run_with_unpause(curl, state, resume_after, timeout)
    return err_list, sio, state, data


def _assert_write_return_replays_data(app, curl, run_with_unpause):
    curl.setopt(pycurl.URL, f"{app}/pause")
    sio = util.BytesIO()
    chunks = []
    state = _pause_state()

    def writefunc(data):
        chunks.append(data)
        if not state["paused"]:
            _pause_now(state)
            return pycurl.WRITEFUNC_PAUSE
        return sio.write(data)

    curl.setopt(pycurl.WRITEFUNCTION, writefunc)
    _, err_list = run_with_unpause(curl, state, resume_after=0.2, timeout=3.0)

    assert not err_list
    assert state["resumed"]
    assert sio.getvalue().decode() == "part1part2"
    assert len(chunks) >= 2
    assert chunks[0] == b"part1"
    assert any(chunk.startswith(b"part1") for chunk in chunks[1:])


def _assert_send_mask(app, curl, run_with_unpause, mask):
    err_list, sio, state, data = _run_upload_pause(
        app, curl, run_with_unpause, mask=mask, resume_after=0.2, timeout=6.0
    )

    assert not err_list
    assert state["resumed"]
    assert state["read_calls"] >= 2
    actual = json.loads(sio.getvalue().decode("ascii"))
    assert actual == data.decode("ascii")


def _assert_read_return(app, curl, run_with_unpause):
    data = b"field1=value1"
    state = _pause_state(offset=0, read_calls=0)

    def readfunc(size):
        state["read_calls"] += 1
        if not state["paused"]:
            _pause_now(state)
            return pycurl.READFUNC_PAUSE
        if state["offset"] < len(data):
            chunk = data[state["offset"] : state["offset"] + size]
            state["offset"] += len(chunk)
            return chunk
        return b""

    curl.setopt(pycurl.URL, f"{app}/postfields")
    curl.setopt(pycurl.POST, 1)
    curl.setopt(pycurl.POSTFIELDSIZE, len(data))
    curl.setopt(pycurl.READFUNCTION, readfunc)

    sio = util.BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)

    _, err_list = run_with_unpause(curl, state, resume_after=0.2, timeout=4.0)

    assert not err_list
    assert state["resumed"]
    assert state["read_calls"] >= 2
    actual = json.loads(sio.getvalue().decode())
    assert actual == {"field1": "value1"}


def _assert_low_speed_timeout(app, curl, run_with_unpause):
    curl.setopt(pycurl.URL, f"{app}/chunks?num_chunks=20&delay=0.2")
    curl.setopt(pycurl.LOW_SPEED_LIMIT, 100)
    curl.setopt(pycurl.LOW_SPEED_TIME, 1)

    sio = util.BytesIO()
    state = _pause_state()
    curl.setopt(pycurl.WRITEFUNCTION, _pause_on_first_write(curl, state, sio))

    done_at, err_list = run_with_unpause(curl, state, resume_after=1.5, timeout=8.0)

    assert state["unpaused_at"] is not None
    assert err_list
    _, err_code, _ = err_list[0]
    assert err_code == pycurl.E_OPERATION_TIMEDOUT
    assert done_at >= state["unpaused_at"]
    assert done_at - state["unpaused_at"] >= 0.8


@pytest.mark.parametrize(
    "mask,resume_after,min_wait",
    [
        (pycurl.PAUSE_RECV, 0.7, 0.6),
        (pycurl.PAUSE_ALL, 1.0, 0.9),
    ],
    ids=["recv", "all"],
)
def test_multi_recv_mask(app, curl, mask, resume_after, min_wait):
    """Pause receiving via mask and ensure data resumes after unpause."""
    start, done_at, err_list, sio, state = _run_download_pause(
        app,
        curl,
        _run_with_unpause_multi,
        mask=mask,
        resume_after=resume_after,
        timeout=4.0,
    )

    assert not err_list
    assert sio.getvalue().decode() == "part1part2"
    assert state["resumed"]
    assert done_at - start > min_wait


@pytest.mark.parametrize(
    "mask",
    [pycurl.PAUSE_RECV, pycurl.PAUSE_ALL],
    ids=["recv", "all"],
)
def test_easy_recv_mask(app, curl, mask):
    """Pause receiving via mask using easy interface and ensure data resumes."""
    start, done_at, err_list, sio, state = _run_download_pause(
        app,
        curl,
        _run_with_unpause_easy,
        mask=mask,
        resume_after=0.2,
        timeout=4.0,
    )

    assert not err_list
    assert state["paused"]
    assert state["resumed"]
    assert state["unpaused_at"] is not None
    assert sio.getvalue().decode() == "part1part2"
    assert done_at >= state["unpaused_at"]


def test_multi_via_write_return_replays_data(app, curl):
    """Pause via WRITEFUNC_PAUSE and ensure first chunk is replayed."""
    _assert_write_return_replays_data(app, curl, _run_with_unpause_multi)


def test_easy_via_write_return_replays_data(app, curl):
    """Pause via WRITEFUNC_PAUSE in easy interface and ensure replay."""
    _assert_write_return_replays_data(app, curl, _run_with_unpause_easy)


@pytest.mark.parametrize(
    "mask",
    [pycurl.PAUSE_SEND, pycurl.PAUSE_ALL],
    ids=["send", "all"],
)
def test_multi_send_mask(app, curl, mask):
    """Pause sending via mask and ensure upload continues after unpause."""
    _assert_send_mask(app, curl, _run_with_unpause_multi, mask)


@pytest.mark.parametrize(
    "mask",
    [pycurl.PAUSE_SEND, pycurl.PAUSE_ALL],
    ids=["send", "all"],
)
def test_easy_send_mask(app, curl, mask):
    """Pause sending via mask using easy interface and ensure upload resumes."""
    _assert_send_mask(app, curl, _run_with_unpause_easy, mask)


def test_multi_via_read_return(app, curl):
    """Pause via READFUNC_PAUSE and ensure upload continues after unpause()."""
    _assert_read_return(app, curl, _run_with_unpause_multi)


def test_easy_via_read_return(app, curl):
    """Pause via READFUNC_PAUSE in easy interface and ensure upload resumes."""
    _assert_read_return(app, curl, _run_with_unpause_easy)


def test_easy_via_read_return_pause_cont_compat(app, curl):
    """Backwards-compat: READFUNC_PAUSE can still resume via pause(PAUSE_CONT)."""

    def run_with_pause_cont(curl, state, resume_after, timeout):
        return _run_with_unpause_easy(
            curl, state, resume_after, timeout, use_pause_cont=True
        )

    _assert_read_return(app, curl, run_with_pause_cont)


def test_multi_excludes_low_speed_limit_and_resets_timer(app, curl):
    """Paused transfers ignore low-speed checks until unpaused."""
    _assert_low_speed_timeout(app, curl, _run_with_unpause_multi)


def test_easy_excludes_low_speed_limit_and_resets_timer(app, curl):
    """Paused transfers ignore low-speed checks until unpaused (easy)."""
    _assert_low_speed_timeout(app, curl, _run_with_unpause_easy)
