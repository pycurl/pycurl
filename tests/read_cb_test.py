from __future__ import annotations

import json
from io import BytesIO
from urllib.parse import urlencode

import pycurl
import pytest

from . import util


POSTFIELDS = {
    "field1": "value1",
    "field2": "value2 with blanks",
    "field3": "value3",
}
POSTSTRING = urlencode(POSTFIELDS)


class DataProvider:
    def __init__(self, data):
        self.data = data
        self.finished = False

    def read_cb(self, size):
        assert len(self.data) <= size
        if not self.finished:
            self.finished = True
            return self.data
        else:
            return ""


def do_post_raw(curl, app, data, read_cb):
    curl.setopt(curl.URL, f"{app}/raw_utf8")
    curl.setopt(curl.POST, 1)
    curl.setopt(curl.HTTPHEADER, ["Content-Type: application/octet-stream"])
    curl.setopt(curl.POSTFIELDSIZE, len(data))
    curl.setopt(curl.READFUNCTION, read_cb)
    sio = BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    curl.perform()
    return json.loads(sio.getvalue().decode("ascii"))


def do_bad_read_callback(
    curl, app, read_cb, post_len=16, expect_code=pycurl.E_ABORTED_BY_CALLBACK
):
    curl.setopt(curl.URL, f"{app}/raw_utf8")
    curl.setopt(curl.POST, 1)
    curl.setopt(curl.HTTPHEADER, ["Content-Type: application/octet-stream"])
    curl.setopt(curl.POSTFIELDSIZE, post_len)
    curl.setopt(curl.READFUNCTION, read_cb)

    with pytest.raises(pycurl.error) as exc_info:
        curl.perform()

    err, msg = exc_info.value.args
    assert err == expect_code


# --- basic POST with read callback ---


def test_post_with_read_callback(curl, app):
    d = DataProvider(POSTSTRING)
    curl.setopt(curl.URL, f"{app}/postfields")
    curl.setopt(curl.POST, 1)
    curl.setopt(curl.POSTFIELDSIZE, len(POSTSTRING))
    curl.setopt(curl.READFUNCTION, d.read_cb)
    sio = BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    curl.perform()

    actual = json.loads(sio.getvalue().decode())
    assert actual == POSTFIELDS


# --- bytes ---


@pytest.mark.parametrize(
    "poststring",
    [
        "world",
        "wor\0ld",
        util.u("Пушкин"),
    ],
)
def test_post_with_read_callback_returning_bytes(curl, app, poststring):
    data = poststring.encode("utf8")
    assert type(data) is bytes
    d = DataProvider(data)
    actual = do_post_raw(curl, app, data, d.read_cb)
    assert actual == poststring


# --- memoryview ---


@pytest.mark.parametrize(
    "poststring",
    [
        "world",
        "wor\0ld",
        util.u("Пушкин"),
    ],
)
def test_post_with_read_callback_returning_memoryview(curl, app, poststring):
    data = memoryview(poststring.encode("utf8"))
    assert type(data) is memoryview
    d = DataProvider(data)
    actual = do_post_raw(curl, app, data, d.read_cb)
    assert actual == poststring


# --- unicode ---


@pytest.mark.parametrize(
    "poststring",
    [
        util.u("world"),
        util.u("wor\0ld"),
    ],
)
def test_post_with_read_callback_returning_unicode(curl, app, poststring):
    assert type(poststring) is str
    d = DataProvider(poststring)

    curl.setopt(curl.URL, f"{app}/raw_utf8")
    curl.setopt(curl.POST, 1)
    curl.setopt(curl.HTTPHEADER, ["Content-Type: application/octet-stream"])
    curl.setopt(curl.POSTFIELDSIZE, len(poststring))
    curl.setopt(curl.READFUNCTION, d.read_cb)
    sio = BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    curl.perform()

    actual = json.loads(sio.getvalue().decode("ascii"))
    assert actual == poststring


def test_post_with_read_callback_returning_unicode_with_multibyte(curl, app):
    poststring = util.u("Пушкин")
    assert type(poststring) is str
    d = DataProvider(poststring)

    curl.setopt(curl.URL, f"{app}/raw_utf8")
    curl.setopt(curl.POST, 1)
    curl.setopt(curl.HTTPHEADER, ["Content-Type: application/octet-stream"])
    curl.setopt(curl.POSTFIELDSIZE, len(poststring))
    curl.setopt(curl.READFUNCTION, d.read_cb)

    with pytest.raises(pycurl.error) as exc_info:
        curl.perform()

    err, msg = exc_info.value.args
    assert err == pycurl.E_ABORTED_BY_CALLBACK
    assert msg == "operation aborted by callback"


# --- numpy array ---

numpy = pytest.importorskip("numpy")


def test_post_with_read_callback_returning_numpy_array(curl, app):
    payload = b"hello numpy"
    arr = numpy.frombuffer(payload, dtype=numpy.uint8)
    d = DataProvider(arr)
    actual = do_post_raw(curl, app, arr, d.read_cb)
    assert actual == payload.decode("ascii")


def test_post_with_read_callback_returning_numpy_tobytes(curl, app):
    """Test numpy array converted to bytes via .tobytes()."""
    payload = b"numpy bytes"
    arr = numpy.frombuffer(payload, dtype=numpy.uint8)
    data = arr.tobytes()
    d = DataProvider(data)
    actual = do_post_raw(curl, app, data, d.read_cb)
    assert actual == payload.decode("ascii")


def test_post_with_read_callback_returning_non_contiguous_numpy(curl, app):
    """A strided (non-contiguous) numpy array cannot satisfy PyBUF_SIMPLE."""
    arr = numpy.arange(10, dtype=numpy.uint8)
    strided = arr[::2]  # non-contiguous view
    assert not strided.flags["C_CONTIGUOUS"]
    do_bad_read_callback(curl, app, lambda _size: strided, post_len=len(strided))


def test_post_with_read_callback_returning_fortran_order_numpy(curl, app):
    """A 2D Fortran-ordered numpy array is not C-contiguous and must be rejected."""
    arr = numpy.array([[1, 2], [3, 4]], dtype=numpy.uint8, order="F")
    assert arr.flags["F_CONTIGUOUS"]
    assert not arr.flags["C_CONTIGUOUS"]
    do_bad_read_callback(curl, app, lambda _size: arr, post_len=arr.nbytes)


# --- pause / resume ---


def test_post_with_read_callback_pause(curl, app):
    data = b"field1=value1"
    paused = False
    resumed = False
    offset = 0

    def read_cb(size):
        nonlocal paused, offset
        if not paused:
            paused = True
            return pycurl.READFUNC_PAUSE
        if offset < len(data):
            take = min(size, len(data) - offset)
            chunk = data[offset : offset + take]
            offset += len(chunk)
            return chunk
        return b""

    curl.setopt(curl.URL, f"{app}/raw_utf8")
    curl.setopt(curl.POST, 1)
    curl.setopt(curl.HTTPHEADER, ["Content-Type: application/octet-stream"])
    curl.setopt(curl.POSTFIELDSIZE, len(data))
    curl.setopt(curl.READFUNCTION, read_cb)
    sio = BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)

    multi = pycurl.CurlMulti()
    multi.add_handle(curl)
    running = True
    while running:
        _, running = multi.perform()
        if paused and not resumed:
            resumed = True
            curl.pause(pycurl.PAUSE_CONT)
        if running:
            multi.select(0.1)
    while True:
        queued, _, err = multi.info_read()
        if err:
            pytest.fail(f"Multi transfer errors: {err}")
        if not queued:
            break

    assert resumed


# --- error cases ---


def test_post_with_read_callback_returning_non_buffer(curl, app):
    do_bad_read_callback(curl, app, lambda size: object())


def test_post_with_read_callback_returning_overly_large_buffer(curl, app):
    do_bad_read_callback(curl, app, lambda size: " " * (size + 1), post_len=1)


def test_post_with_read_callback_that_throws(curl, app):
    def read_cb(size):
        raise RuntimeError("Boom")

    do_bad_read_callback(curl, app, read_cb)


def test_post_with_read_callback_that_aborts(curl, app):
    do_bad_read_callback(curl, app, lambda size: pycurl.READFUNC_ABORT)


def test_post_with_read_callback_that_returns_bad_integer(curl, app):
    do_bad_read_callback(curl, app, lambda size: 5000)


def test_post_with_read_callback_taking_incorrect_args(curl, app):
    def read_cb(too, many, args):
        pass

    do_bad_read_callback(curl, app, read_cb)


def test_post_with_read_callback_not_callable(curl):
    with pytest.raises(TypeError):
        curl.setopt(curl.READFUNCTION, object())


# --- unsetopt ---


def test_readfunction_unsetopt(curl, app):
    curl.setopt(curl.URL, f"{app}/raw_utf8")
    curl.setopt(curl.POST, 1)
    curl.setopt(curl.HTTPHEADER, ["Content-Type: application/octet-stream", "Expect: "])
    curl.setopt(curl.READFUNCTION, None)
    sio = BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)

    curl.perform()
    # did not crash
