import contextlib
import warnings
from io import BytesIO

import pytest

import pycurl

UPLOAD_SIZE = 64

# Older libcurl understands this value but only defines the constant in 7.19.5+
SEEKFUNC_OK = 0

REWIND_OPTIONS = [
    pytest.param(pycurl.SEEKFUNCTION, "seek", id="seek"),
    pytest.param(pycurl.IOCTLFUNCTION, "ioctl", id="ioctl"),
]


@pytest.fixture
def upload_curl(curl, app):
    curl.setopt(pycurl.URL, f"{app}/upload_redirect")
    curl.setopt(pycurl.UPLOAD, 1)
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.INFILESIZE, UPLOAD_SIZE)
    curl.setopt(pycurl.WRITEDATA, BytesIO())
    return curl


def _rewind_with(curl, option, return_value):
    """Install a rewind callback returning return_value, and record its calls."""
    source = BytesIO(b"X" * UPLOAD_SIZE)
    calls = []

    def callback(*args):
        calls.append(args)
        source.seek(0)
        return return_value

    curl.setopt(pycurl.READFUNCTION, source.read)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        curl.setopt(option, callback)
    return calls


@pytest.mark.parametrize("option, callback_name", REWIND_OPTIONS)
def test_rewind_callback_ok(upload_curl, option, callback_name):
    body = BytesIO()
    upload_curl.setopt(pycurl.WRITEDATA, body)
    calls = _rewind_with(upload_curl, option, SEEKFUNC_OK)

    upload_curl.perform()
    assert calls
    assert body.getvalue() == str(UPLOAD_SIZE).encode()


@pytest.mark.parametrize("option, callback_name", REWIND_OPTIONS)
@pytest.mark.parametrize(
    "return_value", [2**31, 2**32], ids=["int32-overflow", "truncates-to-zero"]
)
def test_rewind_callback_oversized_return_is_refused(
    upload_curl, option, callback_name, return_value, capfd
):
    calls = _rewind_with(upload_curl, option, return_value)

    with contextlib.suppress(pycurl.error):
        upload_curl.perform()
    assert calls
    assert (
        f"OverflowError: {callback_name} callback returned {return_value} "
        "which does not fit in an int"
    ) in capfd.readouterr().err
