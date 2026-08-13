import sys
from io import BytesIO

import pycurl
import pytest

from . import util


def test_boolean_value(curl):
    curl.setopt(pycurl.VERBOSE, True)


def test_integer_value(curl):
    curl.setopt(pycurl.VERBOSE, 1)


def test_string_value_for_integer_option(curl):
    with pytest.raises(TypeError):
        curl.setopt(pycurl.VERBOSE, "Hello, world!")


def test_string_value(curl):
    curl.setopt(pycurl.URL, "http://hello.world")


def test_integer_value_for_string_option(curl):
    with pytest.raises(TypeError):
        curl.setopt(pycurl.URL, 1)


def test_float_value_for_integer_option(curl):
    with pytest.raises(TypeError):
        curl.setopt(pycurl.VERBOSE, 1.0)


BLOB_OPTIONS = [
    name
    for name in (
        # libcurl 7.71.0
        "SSLCERT_BLOB",
        "SSLKEY_BLOB",
        "PROXY_SSLCERT_BLOB",
        "PROXY_SSLKEY_BLOB",
        "ISSUERCERT_BLOB",
        "PROXY_ISSUERCERT_BLOB",
        # libcurl 7.77.0
        "CAINFO_BLOB",
        "PROXY_CAINFO_BLOB",
    )
    if hasattr(pycurl, name)
]


@pytest.mark.parametrize("value", [12345, True], ids=["int", "bool"])
@pytest.mark.parametrize("name", BLOB_OPTIONS)
def test_integer_value_for_blob_option(curl, name, value):
    with pytest.raises(TypeError, match="^integers are not supported for this option$"):
        curl.setopt(getattr(pycurl, name), value)


def test_httpheader_list(curl):
    curl.setopt(pycurl.HTTPHEADER, ["Accept:"])


def test_httpheader_tuple(curl):
    curl.setopt(pycurl.HTTPHEADER, ("Accept:",))


def test_httpheader_unicode(curl):
    curl.setopt(pycurl.HTTPHEADER, ("Accept:",))


def _header_echo_url(app):
    return f"{app}/header?h=x-test"


def test_unset_httpheader(app, curl):
    curl.setopt(pycurl.HTTPHEADER, ("x-test: foo",))
    curl.setopt(pycurl.URL, _header_echo_url(app))
    io = BytesIO()
    curl.setopt(pycurl.WRITEDATA, io)
    curl.perform()
    assert io.getvalue() == b"foo"

    curl.unsetopt(pycurl.HTTPHEADER)
    io = BytesIO()
    curl.setopt(pycurl.WRITEDATA, io)
    curl.perform()
    assert io.getvalue() == b""


def test_set_httpheader_none(app, curl):
    curl.setopt(pycurl.HTTPHEADER, ("x-test: foo",))
    curl.setopt(pycurl.URL, _header_echo_url(app))
    io = BytesIO()
    curl.setopt(pycurl.WRITEDATA, io)
    curl.perform()
    assert io.getvalue() == b"foo"

    curl.setopt(pycurl.HTTPHEADER, None)
    io = BytesIO()
    curl.setopt(pycurl.WRITEDATA, io)
    curl.perform()
    assert io.getvalue() == b""


@util.min_libcurl(7, 37, 0)
def test_proxyheader_list(curl):
    curl.setopt(pycurl.PROXYHEADER, ["Accept:"])


@util.min_libcurl(7, 37, 0)
def test_proxyheader_tuple(curl):
    curl.setopt(pycurl.PROXYHEADER, ("Accept:",))


@util.min_libcurl(7, 37, 0)
def test_proxyheader_unicode(curl):
    curl.setopt(pycurl.PROXYHEADER, ("Accept:",))


@util.min_libcurl(7, 37, 0)
def test_unset_proxyheader(curl):
    curl.unsetopt(pycurl.PROXYHEADER)


@util.min_libcurl(7, 37, 0)
def test_set_proxyheader_none(curl):
    curl.setopt(pycurl.PROXYHEADER, None)


def test_unset_encoding(curl):
    curl.unsetopt(pycurl.ENCODING)


# github issue #405
def test_large_options(curl):
    curl.setopt(pycurl.INFILESIZE, 3333858173)
    curl.setopt(pycurl.MAX_RECV_SPEED_LARGE, 3333858173)
    curl.setopt(pycurl.MAX_SEND_SPEED_LARGE, 3333858173)
    curl.setopt(pycurl.MAXFILESIZE, 3333858173)
    curl.setopt(pycurl.POSTFIELDSIZE, 3333858173)
    curl.setopt(pycurl.RESUME_FROM, 3333858173)


@pytest.mark.parametrize(
    "option",
    [
        pycurl.WRITEFUNCTION,
        pycurl.HEADERFUNCTION,
        pycurl.READFUNCTION,
        pycurl.PROGRESSFUNCTION,
        pycurl.XFERINFOFUNCTION,
        pycurl.DEBUGFUNCTION,
        pycurl.IOCTLFUNCTION,
        pycurl.SEEKFUNCTION,
    ],
)
def test_set_callback_none(curl, option):
    curl.setopt(option, None)


def test_httpheader_replace_cycle(app, curl):
    curl.setopt(pycurl.URL, _header_echo_url(app))
    for value in ("a", "b", "c", "d"):
        curl.setopt(pycurl.HTTPHEADER, [f"x-test: {value}"])
    io = BytesIO()
    curl.setopt(pycurl.WRITEDATA, io)
    curl.perform()
    assert io.getvalue() == b"d"


def test_httppost_non_text_field_name(curl):
    with (
        pytest.warns(DeprecationWarning, match="HTTPPOST is deprecated; use MIMEPOST"),
        pytest.raises(
            TypeError,
            match=(
                r"^list or tuple must contain a byte string or Unicode string "
                r"with ASCII code points only as first element$"
            ),
        ),
    ):
        curl.setopt(pycurl.HTTPPOST, [(1, b"value")])


def test_httpheader_replace_refcount(curl):
    first = ["x-test: first"]
    before = sys.getrefcount(first)
    curl.setopt(pycurl.HTTPHEADER, first)
    curl.setopt(pycurl.HTTPHEADER, ["x-test: second"])
    assert sys.getrefcount(first) == before
