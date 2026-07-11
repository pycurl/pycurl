from __future__ import annotations

import builtins
import os.path
import sys
import urllib.request

import pycurl
import pytest

from . import util


# Empty tuple on 3.10 so isinstance(x, _BaseExceptionGroup) is harmlessly False.
_BaseExceptionGroup = getattr(builtins, "BaseExceptionGroup", ())

_FILE_URL = "file:" + urllib.request.pathname2url(os.path.abspath(__file__))


def _raise_runtime(*_a, **_kw):
    raise RuntimeError("boom")


def _discard(_data):
    return None


def _walk_leaves(exc):
    if isinstance(exc, _BaseExceptionGroup):
        for sub in exc.exceptions:
            yield from _walk_leaves(sub)
    else:
        yield exc


def _assert_cause_includes(err, exc_type, message=None):
    # __cause__ is the exception itself, or an ExceptionGroup of them on 3.11+.
    cause = err.__cause__
    assert cause is not None, f"expected a __cause__, got None on {err!r}"
    leaves = [e for e in _walk_leaves(cause) if isinstance(e, exc_type)]
    assert leaves, f"no {exc_type.__name__} in {cause!r}"
    if message is not None:
        assert any(str(e) == message for e in leaves)
    # the original traceback survives on the raised exception(s)
    assert all(e.__traceback__ is not None for e in leaves)


@pytest.fixture
def file_curl():
    c = util.DefaultCurl()
    c.setopt(pycurl.URL, _FILE_URL)
    yield c
    c.close()


def _cfg_write(curl, app):
    curl.setopt(pycurl.URL, _FILE_URL)
    curl.setopt(pycurl.WRITEFUNCTION, _raise_runtime)


def _cfg_header(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    curl.setopt(pycurl.WRITEFUNCTION, _discard)
    curl.setopt(pycurl.HEADERFUNCTION, _raise_runtime)


def _cfg_read(curl, app):
    curl.setopt(pycurl.URL, f"{app}/postfields")
    curl.setopt(pycurl.POST, 1)
    curl.setopt(pycurl.POSTFIELDSIZE, 16)
    curl.setopt(pycurl.WRITEFUNCTION, _discard)
    curl.setopt(pycurl.READFUNCTION, _raise_runtime)


def _cfg_progress(curl, app):
    curl.setopt(pycurl.URL, _FILE_URL)
    curl.setopt(pycurl.WRITEFUNCTION, _discard)
    curl.setopt(pycurl.NOPROGRESS, 0)
    with pytest.warns(DeprecationWarning, match="PROGRESSFUNCTION is deprecated"):
        curl.setopt(pycurl.PROGRESSFUNCTION, _raise_runtime)


def _cfg_xferinfo(curl, app):
    curl.setopt(pycurl.URL, _FILE_URL)
    curl.setopt(pycurl.WRITEFUNCTION, _discard)
    curl.setopt(pycurl.NOPROGRESS, 0)
    curl.setopt(pycurl.XFERINFOFUNCTION, _raise_runtime)


def _cfg_opensocket(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    curl.setopt(pycurl.WRITEFUNCTION, _discard)
    curl.setopt(pycurl.OPENSOCKETFUNCTION, _raise_runtime)


def _cfg_sockopt(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    curl.setopt(pycurl.WRITEFUNCTION, _discard)
    curl.setopt(pycurl.SOCKOPTFUNCTION, _raise_runtime)


@pytest.mark.parametrize(
    "configure",
    [
        _cfg_write,
        _cfg_header,
        _cfg_read,
        _cfg_progress,
        _cfg_xferinfo,
        _cfg_opensocket,
        _cfg_sockopt,
    ],
    ids=["write", "header", "read", "progress", "xferinfo", "opensocket", "sockopt"],
)
def test_callback_exception_becomes_cause(configure, curl, app):
    configure(curl, app)
    with pytest.raises(pycurl.error) as excinfo:
        curl.perform()
    _assert_cause_includes(excinfo.value, RuntimeError, "boom")


def test_cause_preserves_message_and_attributes(file_curl):
    class Boom(Exception):
        pass

    def write_cb(_data):
        err = Boom("kaboom")
        err.detail = 42
        raise err

    file_curl.setopt(pycurl.WRITEFUNCTION, write_cb)
    with pytest.raises(pycurl.error) as excinfo:
        file_curl.perform()
    cause = excinfo.value.__cause__
    assert isinstance(cause, Boom)
    assert str(cause) == "kaboom"
    assert cause.detail == 42


def test_callback_exception_with_existing_cause_is_preserved(file_curl):
    def write_cb(_data):
        try:
            raise ValueError("inner")
        except ValueError as inner:
            raise RuntimeError("outer") from inner

    file_curl.setopt(pycurl.WRITEFUNCTION, write_cb)
    with pytest.raises(pycurl.error) as excinfo:
        file_curl.perform()
    _assert_cause_includes(excinfo.value, RuntimeError, "outer")
    (outer,) = _walk_leaves(excinfo.value.__cause__)
    assert isinstance(outer.__cause__, ValueError)
    assert str(outer.__cause__) == "inner"


def test_callback_exception_still_printed_to_stderr(file_curl, capfd):
    file_curl.setopt(pycurl.WRITEFUNCTION, _raise_runtime)
    with pytest.raises(pycurl.error):
        file_curl.perform()
    captured = capfd.readouterr()
    assert "Traceback" in captured.err
    assert "RuntimeError: boom" in captured.err


@pytest.mark.parametrize(
    "exc, exc_type",
    [
        (KeyboardInterrupt(), KeyboardInterrupt),
        (SystemExit(7), SystemExit),
        (GeneratorExit(), GeneratorExit),
    ],
    ids=["KeyboardInterrupt", "SystemExit", "GeneratorExit"],
)
def test_base_exception_propagates_unchanged(file_curl, exc, exc_type):
    def write_cb(_data):
        raise exc

    file_curl.setopt(pycurl.WRITEFUNCTION, write_cb)
    with pytest.raises(exc_type) as excinfo:
        file_curl.perform()
    assert excinfo.type is exc_type
    assert excinfo.value.__cause__ is None


def test_system_exit_preserves_code(file_curl):
    def write_cb(_data):
        raise SystemExit(7)

    file_curl.setopt(pycurl.WRITEFUNCTION, write_cb)
    with pytest.raises(SystemExit) as excinfo:
        file_curl.perform()
    assert excinfo.value.code == 7


def test_no_stale_cause_after_failed_then_successful_perform(file_curl):
    file_curl.setopt(pycurl.WRITEFUNCTION, _raise_runtime)
    with pytest.raises(pycurl.error) as excinfo:
        file_curl.perform()
    assert isinstance(excinfo.value.__cause__, RuntimeError)

    file_curl.setopt(pycurl.WRITEFUNCTION, _discard)
    file_curl.perform()

    file_curl.setopt(pycurl.WRITEFUNCTION, lambda _data: -1)
    with pytest.raises(pycurl.error) as excinfo:
        file_curl.perform()
    assert excinfo.value.__cause__ is None


def test_pycurl_error_without_callback_exception_has_no_cause(curl, free_port):
    curl.setopt(pycurl.URL, f"http://127.0.0.1:{free_port}/")
    curl.setopt(pycurl.CONNECTTIMEOUT, 1)
    with pytest.raises(pycurl.error) as excinfo:
        curl.perform()
    assert excinfo.value.__cause__ is None


def test_debug_cb_capture_does_not_leak_to_setopt(file_curl):
    def debug_cb(_type, _buf):
        raise RuntimeError("stale debug")

    file_curl.setopt(pycurl.VERBOSE, 1)
    file_curl.setopt(pycurl.DEBUGFUNCTION, debug_cb)
    file_curl.setopt(pycurl.WRITEFUNCTION, _discard)
    file_curl.perform()

    file_curl.setopt(pycurl.DEBUGFUNCTION, None)
    with pytest.raises(pycurl.error) as excinfo:
        file_curl.setopt(pycurl.PROXYTYPE, 999999)
    assert excinfo.value.__cause__ is None


def test_first_callback_to_raise_wins(app, curl):
    # HEADERFUNCTION runs (and aborts) before WRITEFUNCTION.
    seen = []

    def header_cb(_data):
        seen.append("header")
        raise ValueError("header err")

    def write_cb(_data):
        seen.append("write")
        raise RuntimeError("write err")

    curl.setopt(pycurl.URL, f"{app}/success")
    curl.setopt(pycurl.HEADERFUNCTION, header_cb)
    curl.setopt(pycurl.WRITEFUNCTION, write_cb)
    with pytest.raises(pycurl.error) as excinfo:
        curl.perform()
    assert seen[0] == "header"
    _assert_cause_includes(excinfo.value, ValueError, "header err")


def test_debug_cb_exception_alone_does_not_abort(file_curl):
    file_curl.setopt(pycurl.VERBOSE, 1)
    file_curl.setopt(pycurl.DEBUGFUNCTION, _raise_runtime)
    file_curl.setopt(pycurl.WRITEFUNCTION, _discard)
    file_curl.perform()


def test_closesocket_cb_exception_is_printed_not_lost(app, curl, capfd):
    # libcurl ignores CLOSESOCKETFUNCTION's return, so a raise cannot abort the
    # (successful) transfer; it must be printed, not silently dropped.
    def close_socket(_curlfd):
        raise RuntimeError("close boom")

    curl.setopt(pycurl.URL, f"{app}/success")
    curl.setopt(pycurl.WRITEFUNCTION, _discard)
    curl.setopt(pycurl.CLOSESOCKETFUNCTION, close_socket)
    curl.perform()
    assert "RuntimeError: close boom" in capfd.readouterr().err


@pytest.mark.skipif(
    sys.version_info < (3, 11), reason="ExceptionGroup added in Python 3.11"
)
def test_multiple_captures_wrap_in_exception_group(file_curl):
    file_curl.setopt(pycurl.VERBOSE, 1)

    def debug_cb(_type, _buf):
        raise RuntimeError("debug boom")

    file_curl.setopt(pycurl.DEBUGFUNCTION, debug_cb)
    file_curl.setopt(pycurl.WRITEFUNCTION, lambda _b: -1)
    with pytest.raises(pycurl.error) as excinfo:
        file_curl.perform()
    cause = excinfo.value.__cause__
    assert isinstance(cause, _BaseExceptionGroup)
    leaves = list(_walk_leaves(cause))
    assert len(leaves) >= 2
    assert all(isinstance(e, RuntimeError) for e in leaves)


def test_debug_cb_exception_surfaces_when_other_callback_fails(file_curl):
    file_curl.setopt(pycurl.VERBOSE, 1)

    def debug_cb(_type, _buf):
        raise RuntimeError("debug boom")

    file_curl.setopt(pycurl.DEBUGFUNCTION, debug_cb)
    file_curl.setopt(pycurl.WRITEFUNCTION, lambda _b: -1)
    with pytest.raises(pycurl.error) as excinfo:
        file_curl.perform()
    _assert_cause_includes(excinfo.value, RuntimeError, "debug boom")
