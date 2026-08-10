import copy
import gc
import io
import pickle
import weakref

import pytest

import pycurl

from . import util

pytestmark = pytest.mark.skipif(
    not hasattr(pycurl, "CurlUrl"), reason="libcurl without URL API (< 7.62.0)"
)

FULL_URL = "https://user:pw@example.com:8080/a/b?x=1#frag"


def test_construct_empty():
    u = pycurl.CurlUrl()
    assert u.scheme is None
    assert u.host is None
    with pytest.raises(pycurl.error):
        str(u)


def test_construct_from_url():
    u = pycurl.CurlUrl(FULL_URL)
    assert u.scheme == "https"
    assert u.user == "user"
    assert u.password == "pw"
    assert u.host == "example.com"
    assert u.port == "8080"
    assert u.path == "/a/b"
    assert u.query == "x=1"
    assert u.fragment == "frag"
    assert u.url == FULL_URL


def test_absent_part_is_none():
    u = pycurl.CurlUrl("https://example.com/")
    assert u.fragment is None
    assert u.query is None
    assert u.user is None
    assert u.options is None


def test_construct_invalid_raises():
    with pytest.raises(pycurl.error) as excinfo:
        pycurl.CurlUrl("this is not a url")
    assert isinstance(excinfo.value.args[0], int)


def test_construct_with_flags():
    u = pycurl.CurlUrl(
        "example.com/path", flags=pycurl.U_DEFAULT_SCHEME | pycurl.U_GUESS_SCHEME
    )
    assert u.host == "example.com"
    assert u.scheme is not None


def test_construct_from_bytes():
    u = pycurl.CurlUrl(b"https://example.com/")
    assert u.host == "example.com"


def test_set_components():
    u = pycurl.CurlUrl("https://example.com/")
    u.scheme = "http"
    u.host = "example.org"
    u.path = "/x"
    u.query = "a=1"
    u.fragment = "top"
    assert u.url == "http://example.org/x?a=1#top"


def test_set_none_removes():
    u = pycurl.CurlUrl(FULL_URL)
    u.fragment = None
    assert u.fragment is None
    assert "#" not in str(u)


def test_del_removes():
    u = pycurl.CurlUrl(FULL_URL)
    del u.query
    assert u.query is None
    assert "?" not in str(u)


def test_port_accepts_int_and_str():
    u = pycurl.CurlUrl("https://example.com/")
    u.port = 9090
    assert u.port == "9090"
    u.port = "1234"
    assert u.port == "1234"


def test_str_roundtrip():
    u = pycurl.CurlUrl(FULL_URL)
    assert str(u) == FULL_URL


def test_str_incomplete_raises():
    u = pycurl.CurlUrl()
    u.path = "/only-a-path"
    with pytest.raises(pycurl.error):
        str(u)


def test_repr_never_raises():
    complete = pycurl.CurlUrl("https://example.com/")
    assert "example.com" in repr(complete)
    incomplete = pycurl.CurlUrl()
    assert "incomplete" in repr(incomplete)


def test_getpart_setpart_roundtrip():
    u = pycurl.CurlUrl(FULL_URL)
    assert u.getpart(pycurl.UPART_HOST) == "example.com"
    u.setpart(pycurl.UPART_HOST, "example.net")
    assert u.host == "example.net"


def test_getpart_absent_is_none():
    u = pycurl.CurlUrl("https://example.com/")
    assert u.getpart(pycurl.UPART_FRAGMENT) is None


def test_setpart_urlencode_and_urldecode():
    u = pycurl.CurlUrl("https://example.com/")
    u.setpart(pycurl.UPART_QUERY, "a=b c", pycurl.U_URLENCODE)
    raw = u.getpart(pycurl.UPART_QUERY)
    assert raw != "a=b c"
    assert " " not in raw
    assert u.getpart(pycurl.UPART_QUERY, pycurl.U_URLDECODE) == "a=b c"


def test_setpart_appendquery():
    u = pycurl.CurlUrl("https://example.com/?a=1")
    u.setpart(pycurl.UPART_QUERY, "b=2", pycurl.U_APPENDQUERY)
    assert u.query == "a=1&b=2"


def test_setpart_remove_with_none():
    u = pycurl.CurlUrl(FULL_URL)
    u.setpart(pycurl.UPART_FRAGMENT, None)
    assert u.fragment is None


def test_getpart_bad_part_raises():
    u = pycurl.CurlUrl("https://example.com/")
    with pytest.raises(pycurl.error):
        u.getpart(9999)


def test_setpart_bad_value_type():
    u = pycurl.CurlUrl("https://example.com/")
    with pytest.raises(TypeError):
        u.setpart(pycurl.UPART_HOST, 123)


def test_copy_is_independent():
    u = pycurl.CurlUrl(FULL_URL)
    v = copy.copy(u)
    v.host = "changed.example"
    assert u.host == "example.com"
    assert v.host == "changed.example"


def test_deepcopy_is_independent():
    u = pycurl.CurlUrl(FULL_URL)
    v = copy.deepcopy(u)
    v.scheme = "http"
    assert u.scheme == "https"
    assert v.scheme == "http"


def test_pickle_raises():
    u = pycurl.CurlUrl(FULL_URL)
    with pytest.raises((TypeError, pickle.PicklingError)):
        pickle.dumps(u)


def test_weakref_and_gc():
    u = pycurl.CurlUrl(FULL_URL)
    ref = weakref.ref(u)
    assert ref() is u
    del u
    gc.collect()
    assert ref() is None


def test_no_reference_leak():
    for _ in range(500):
        u = pycurl.CurlUrl("https://example.com/p?q=1")
        u.host = "example.org"
    gc.collect()


@util.min_libcurl(7, 65, 0)
def test_zoneid():
    u = pycurl.CurlUrl("https://[fe80::1%25eth0]/")
    assert u.zoneid == "eth0"
    u.zoneid = "eth1"
    assert u.zoneid == "eth1"


def test_version_gate_meta():
    supported = pycurl.COMPILE_LIBCURL_VERSION_NUM >= 0x073E00
    assert hasattr(pycurl, "CurlUrl") == supported
    assert hasattr(pycurl, "UPART_URL") == supported


@util.min_libcurl(7, 63, 0)
def test_curlu_option_transfer(curl, app):
    u = pycurl.CurlUrl(f"{app}/success")
    buf = io.BytesIO()
    curl.setopt(pycurl.CURLU, u)
    curl.setopt(pycurl.WRITEDATA, buf)
    curl.perform()
    assert buf.getvalue() == b"success"
    assert curl.getinfo(pycurl.EFFECTIVE_URL) == f"{app}/success"


@util.min_libcurl(7, 63, 0)
def test_curlu_option_keeps_url_alive(curl, app):
    u = pycurl.CurlUrl(f"{app}/success")
    ref = weakref.ref(u)
    curl.setopt(pycurl.CURLU, u)
    del u
    gc.collect()
    assert ref() is not None
    buf = io.BytesIO()
    curl.setopt(pycurl.WRITEDATA, buf)
    curl.perform()
    assert buf.getvalue() == b"success"


@util.min_libcurl(7, 63, 0)
def test_curlu_option_mutation_between_transfers(curl, app):
    u = pycurl.CurlUrl(f"{app}/success")
    curl.setopt(pycurl.CURLU, u)
    buf = io.BytesIO()
    curl.setopt(pycurl.WRITEDATA, buf)
    curl.perform()
    assert buf.getvalue() == b"success"
    assert curl.getinfo(pycurl.HTTP_CODE) == 200

    u.path = "/status/404"
    buf2 = io.BytesIO()
    curl.setopt(pycurl.WRITEDATA, buf2)
    curl.perform()
    assert buf2.getvalue() == b"not found"
    assert curl.getinfo(pycurl.HTTP_CODE) == 404


@util.min_libcurl(7, 63, 0)
def test_curlu_option_unset(curl, app):
    u = pycurl.CurlUrl(f"{app}/success")
    curl.setopt(pycurl.CURLU, u)
    curl.unsetopt(pycurl.CURLU)
    buf = io.BytesIO()
    curl.setopt(pycurl.URL, f"{app}/success")
    curl.setopt(pycurl.WRITEDATA, buf)
    curl.perform()
    assert buf.getvalue() == b"success"


@util.min_libcurl(7, 63, 0)
def test_curlu_option_duphandle_shares_url():
    u = pycurl.CurlUrl("https://example.com/")
    ref = weakref.ref(u)
    c = pycurl.Curl()
    d = None
    try:
        c.setopt(pycurl.CURLU, u)
        d = c.duphandle()
        del u
        gc.collect()
        assert ref() is not None
        c.close()
        gc.collect()
        assert ref() is not None
    finally:
        c.close()
        if d is not None:
            d.close()
    gc.collect()
    assert ref() is None


@util.min_libcurl(7, 63, 0)
def test_curlu_option_wrong_type():
    c = util.DefaultCurl()
    try:
        with pytest.raises((TypeError, pycurl.error)):
            c.setopt(pycurl.CURLU, "https://example.com/")
    finally:
        c.close()
