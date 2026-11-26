import io

import pytest

import pycurl

from . import util


def _post(curl, app):
    body = io.BytesIO()
    curl.setopt(pycurl.URL, f"{app}/upload_target")
    curl.setopt(pycurl.WRITEFUNCTION, body.write)
    curl.perform()
    return int(body.getvalue())


@pytest.mark.parametrize("option", ["POSTFIELDSIZE", "POSTFIELDSIZE_LARGE"])
def test_size_larger_than_postfields_rejected(curl, option):
    curl.setopt(pycurl.POSTFIELDS, b"0123456789")
    with pytest.raises(ValueError, match="exceeds the 10 bytes"):
        curl.setopt(getattr(pycurl, option), 4096)


@pytest.mark.parametrize("option", ["POSTFIELDSIZE", "POSTFIELDSIZE_LARGE"])
def test_size_larger_than_copypostfields_rejected(curl, option):
    curl.setopt(pycurl.COPYPOSTFIELDS, b"0123456789")
    with pytest.raises(ValueError, match="exceeds the 10 bytes"):
        curl.setopt(getattr(pycurl, option), 4096)


def test_unicode_postfields_length_is_encoded_length(curl):
    curl.setopt(pycurl.POSTFIELDS, "abc")
    curl.setopt(pycurl.POSTFIELDSIZE, 3)
    with pytest.raises(ValueError):
        curl.setopt(pycurl.POSTFIELDSIZE, 4)


def test_smaller_size_sends_prefix(curl, app):
    curl.setopt(pycurl.POSTFIELDS, b"0123456789")
    curl.setopt(pycurl.POSTFIELDSIZE, 4)
    assert _post(curl, app) == 4


@pytest.mark.parametrize("option", ["POSTFIELDS", "COPYPOSTFIELDS"])
def test_negative_size_allowed(curl, app, option):
    # bytes objects are NUL-terminated, so libcurl's strlen() stays in bounds
    curl.setopt(getattr(pycurl, option), b"0123456789")
    curl.setopt(pycurl.POSTFIELDSIZE, -1)
    assert _post(curl, app) == 10


def test_copypostfields_ignores_stale_size(curl, app):
    # a size set for an earlier request used to make libcurl copy past the data
    curl.setopt(pycurl.POSTFIELDSIZE, 4096)
    curl.setopt(pycurl.COPYPOSTFIELDS, b"0123456789")
    assert _post(curl, app) == 10


def test_copypostfields_allows_embedded_nul(curl, app):
    curl.setopt(pycurl.COPYPOSTFIELDS, b"abc\0def")
    assert _post(curl, app) == 7


def test_copypostfields_kept_when_size_grows(curl, app):
    # libcurl drops its own copy when the size grows and reads stdin instead
    curl.setopt(pycurl.COPYPOSTFIELDS, b"0123456789")
    curl.setopt(pycurl.POSTFIELDSIZE, 5)
    curl.setopt(pycurl.POSTFIELDSIZE, 6)
    assert _post(curl, app) == 6


def test_size_unrestricted_without_postfields(curl):
    # POSTFIELDSIZE with READFUNCTION announces the body length
    curl.setopt(pycurl.POSTFIELDSIZE, 4096)
    curl.setopt(pycurl.POSTFIELDSIZE_LARGE, 1 << 40)


def test_reset_clears_limit(curl):
    curl.setopt(pycurl.POSTFIELDS, b"0123456789")
    curl.reset()
    curl.setopt(pycurl.POSTFIELDSIZE, 4096)


def test_duphandle_keeps_limit(curl):
    curl.setopt(pycurl.COPYPOSTFIELDS, b"0123456789")
    dup = curl.duphandle()
    try:
        with pytest.raises(ValueError, match="exceeds the 10 bytes"):
            dup.setopt(pycurl.POSTFIELDSIZE, 4096)
    finally:
        dup.close()


def test_new_postfields_replaces_limit(curl):
    curl.setopt(pycurl.COPYPOSTFIELDS, b"0123456789")
    curl.setopt(pycurl.POSTFIELDS, b"x" * 100)
    curl.setopt(pycurl.POSTFIELDSIZE, 100)


def test_setopt_string_path_checked():
    curl = util.DefaultCurl()
    try:
        curl.setopt_string(pycurl.POSTFIELDS, "0123456789")
        with pytest.raises(ValueError):
            curl.setopt(pycurl.POSTFIELDSIZE, 11)
    finally:
        curl.close()
