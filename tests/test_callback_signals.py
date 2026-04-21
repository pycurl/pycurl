#! /usr/bin/env python
# vi:ts=4:et

import os
import select
import signal
import subprocess
import sys
import time
from pathlib import Path
from io import BytesIO

import pycurl
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
THIS_FILE = Path(__file__).resolve()

HAS_XFERINFOFUNCTION = hasattr(pycurl, "XFERINFOFUNCTION")
SUBPROCESS_WAIT_TIMEOUT = 45.0
SIGINT_PROBE_SLEEP = 10.0


@pytest.fixture
def callback_curl(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    body = BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, body.write)
    return curl


def test_header_callback_keyboard_interrupt(callback_curl):
    def header_function(_):
        raise KeyboardInterrupt()

    callback_curl.setopt(pycurl.HEADERFUNCTION, header_function)

    with pytest.raises(KeyboardInterrupt):
        callback_curl.perform()


def test_write_callback_keyboard_interrupt(callback_curl):
    called = {"called": False}

    def write_function(_):
        called["called"] = True
        raise KeyboardInterrupt()

    callback_curl.setopt(pycurl.WRITEFUNCTION, write_function)

    with pytest.raises(KeyboardInterrupt):
        callback_curl.perform()

    assert called["called"]


def test_opensocket_callback_keyboard_interrupt(callback_curl):
    called = {"called": False}

    def opensocket_function(_purpose, _curl_address):
        called["called"] = True
        raise KeyboardInterrupt()

    callback_curl.setopt(pycurl.OPENSOCKETFUNCTION, opensocket_function)

    with pytest.raises(KeyboardInterrupt):
        callback_curl.perform()

    assert called["called"]


def test_read_callback_keyboard_interrupt(curl, app):
    called = {"called": False}
    curl.setopt(pycurl.URL, f"{app}/raw_utf8")
    curl.setopt(pycurl.POST, 1)
    curl.setopt(pycurl.POSTFIELDSIZE, 1)
    curl.setopt(pycurl.HTTPHEADER, ["Content-Type: application/octet-stream"])

    def read_function(_size):
        called["called"] = True
        raise KeyboardInterrupt()

    curl.setopt(pycurl.READFUNCTION, read_function)

    with pytest.raises(KeyboardInterrupt):
        curl.perform()

    assert called["called"]


def test_progress_callback_keyboard_interrupt(curl, app):
    called = {"called": False}
    curl.setopt(pycurl.URL, f"{app}/long_pause")
    curl.setopt(pycurl.NOPROGRESS, False)

    def progress_function(_dltotal, _dlnow, _ultotal, _ulnow):
        called["called"] = True
        raise KeyboardInterrupt()

    with pytest.warns(DeprecationWarning, match="PROGRESSFUNCTION is deprecated; use XFERINFOFUNCTION"):
        curl.setopt(pycurl.PROGRESSFUNCTION, progress_function)

    with pytest.raises(KeyboardInterrupt):
        curl.perform()

    assert called["called"]


@pytest.mark.skipif(
    not HAS_XFERINFOFUNCTION,
    reason="XFERINFOFUNCTION is not available with this libcurl",
)
def test_xferinfo_callback_keyboard_interrupt(curl, app):
    called = {"called": False}
    curl.setopt(pycurl.URL, f"{app}/long_pause")
    curl.setopt(pycurl.NOPROGRESS, False)

    def xferinfo_function(_dltotal, _dlnow, _ultotal, _ulnow):
        called["called"] = True
        raise KeyboardInterrupt()

    curl.setopt(pycurl.XFERINFOFUNCTION, xferinfo_function)

    with pytest.raises(KeyboardInterrupt):
        curl.perform()

    assert called["called"]


def test_header_callback_non_interrupt_exception(callback_curl):
    def header_function(_):
        raise ValueError("boom")

    callback_curl.setopt(pycurl.HEADERFUNCTION, header_function)

    with pytest.raises(pycurl.error) as excinfo:
        callback_curl.perform()

    assert excinfo.value.args[0] == pycurl.E_WRITE_ERROR


def test_header_callback_system_exit(callback_curl):
    def header_function(_):
        raise SystemExit(3)

    callback_curl.setopt(pycurl.HEADERFUNCTION, header_function)

    with pytest.raises(SystemExit) as excinfo:
        callback_curl.perform()

    assert excinfo.value.code == 3


def _run_sigint_probe(url):
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, url)

    def write_cb(data):
        print("CALLBACK_ENTER", flush=True)
        time.sleep(SIGINT_PROBE_SLEEP)
        return len(data)

    curl.setopt(pycurl.WRITEFUNCTION, write_cb)

    try:
        curl.perform()
    except KeyboardInterrupt:
        print("RESULT:KEYBOARDINTERRUPT", flush=True)
        return 130
    except pycurl.error as exc:
        print("RESULT:PYCURL_ERROR:%s" % (exc.args[0],), flush=True)
        return 2
    else:
        print("RESULT:OK", flush=True)
        return 0
    finally:
        curl.close()


def _run_sigint_detection_probe(url):
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, url)

    state = {"calls": 0}

    def write_cb(data):
        state["calls"] += 1
        print("CALLBACK_COUNT:%d" % (state["calls"],), flush=True)
        return len(data)

    curl.setopt(pycurl.WRITEFUNCTION, write_cb)

    try:
        curl.perform()
    except KeyboardInterrupt:
        print("RESULT:KEYBOARDINTERRUPT:CALLS:%d" % (state["calls"],), flush=True)
        return 130
    except pycurl.error as exc:
        print(
            "RESULT:PYCURL_ERROR:%s:CALLS:%d" % (exc.args[0], state["calls"]),
            flush=True,
        )
        return 2
    else:
        print("RESULT:OK:CALLS:%d" % (state["calls"],), flush=True)
        return 0
    finally:
        curl.close()


def _wait_for_stdout_line(proc, expected_line, timeout):
    if proc.stdout is None:
        return False, ""

    deadline = time.monotonic() + timeout
    fd = proc.stdout.fileno()
    expected = expected_line.encode("utf-8")
    output = bytearray()
    pending = b""

    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        ready, _, _ = select.select([fd], [], [], min(0.2, max(0.0, remaining)))
        if not ready:
            if proc.poll() is not None:
                break
            continue

        chunk = os.read(fd, 4096)
        if not chunk:
            if proc.poll() is not None:
                break
            continue

        pending += chunk

        while b"\n" in pending:
            raw_line, pending = pending.split(b"\n", 1)
            output.extend(raw_line)
            output.extend(b"\n")
            if raw_line.rstrip(b"\r") == expected:
                output.extend(pending)
                return True, _decode_subprocess_output(bytes(output))

    output.extend(pending)
    return False, _decode_subprocess_output(bytes(output))


def _decode_subprocess_output(output):
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", "replace")
    return output


def _start_sigint_probe_subprocess(probe_arg, url):
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    root = str(PROJECT_ROOT)
    if pythonpath:
        env["PYTHONPATH"] = root + os.pathsep + pythonpath
    else:
        env["PYTHONPATH"] = root

    return subprocess.Popen(
        [
            sys.executable,
            "-u",
            str(THIS_FILE),
            probe_arg,
            url,
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
        bufsize=0,
    )


def _main():
    if len(sys.argv) == 3 and sys.argv[1] == "--sigint-probe":
        return _run_sigint_probe(sys.argv[2])
    if len(sys.argv) == 3 and sys.argv[1] == "--sigint-detect-probe":
        return _run_sigint_detection_probe(sys.argv[2])
    return 0


@pytest.mark.skipif(
    sys.platform == "win32", reason="SIGINT behavior differs on Windows"
)
def test_sigint_from_parent_process_propagates_as_keyboardinterrupt(app):
    proc = _start_sigint_probe_subprocess("--sigint-probe", f"{app}/success")
    captured = ""
    out = b""

    try:
        saw_callback, captured = _wait_for_stdout_line(
            proc, "CALLBACK_ENTER", timeout=SUBPROCESS_WAIT_TIMEOUT
        )
        if not saw_callback:
            if proc.poll() is None:
                proc.kill()
            out, _ = proc.communicate()
            output = captured + _decode_subprocess_output(out)
            pytest.fail(
                f"Child process never entered callback: returncode={proc.returncode}, output={output}"
            )

        proc.send_signal(signal.SIGINT)
        try:
            out, _ = proc.communicate(timeout=SUBPROCESS_WAIT_TIMEOUT)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
            output = captured + _decode_subprocess_output(out)
            pytest.fail(
                f"Timed out waiting for SIGINT probe to exit: returncode={proc.returncode}, output={output}"
            )
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate()

    output = captured + _decode_subprocess_output(out)

    assert proc.returncode == 130, f"returncode={proc.returncode}, output={output}"
    assert "RESULT:KEYBOARDINTERRUPT" in output
    assert "RESULT:PYCURL_ERROR" not in output


@pytest.mark.skipif(
    sys.platform == "win32", reason="SIGINT behavior differs on Windows"
)
def test_sigint_detected_before_second_write_callback_invocation(app):
    proc = _start_sigint_probe_subprocess(
        "--sigint-detect-probe", f"{app}/chunks?num_chunks=2&delay=3"
    )
    captured = ""
    out = b""

    try:
        saw_first_write, captured = _wait_for_stdout_line(
            proc, "CALLBACK_COUNT:1", timeout=SUBPROCESS_WAIT_TIMEOUT
        )
        if not saw_first_write:
            if proc.poll() is None:
                proc.kill()
            out, _ = proc.communicate()
            output = captured + _decode_subprocess_output(out)
            pytest.fail(
                f"Child process never reached first write callback: returncode={proc.returncode}, output={output}"
            )

        proc.send_signal(signal.SIGINT)
        try:
            out, _ = proc.communicate(timeout=SUBPROCESS_WAIT_TIMEOUT)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
            output = captured + _decode_subprocess_output(out)
            pytest.fail(
                f"Timed out waiting for SIGINT detect probe to exit: returncode={proc.returncode}, output={output}"
            )
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate()

    output = captured + _decode_subprocess_output(out)

    assert proc.returncode == 130, f"returncode={proc.returncode}, output={output}"
    assert "RESULT:KEYBOARDINTERRUPT:CALLS:1" in output
    assert "CALLBACK_COUNT:2" not in output


if __name__ == "__main__":
    raise SystemExit(_main())
