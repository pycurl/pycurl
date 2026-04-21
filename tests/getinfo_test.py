import flaky
import pycurl
import pytest
from io import BytesIO

from . import localhost, util

DEPRECATED_STR = "getinfo option is deprecated"

@flaky.flaky(max_runs=3)
def test_getinfo(curl, app):
    make_request(curl, app)

    assert 200 == curl.getinfo(pycurl.HTTP_CODE)
    assert 200 == curl.getinfo(pycurl.RESPONSE_CODE)
    assert type(curl.getinfo(pycurl.TOTAL_TIME)) is float
    with pytest.warns(DeprecationWarning, match=DEPRECATED_STR):
        assert type(curl.getinfo(pycurl.SPEED_DOWNLOAD)) is float
    with pytest.warns(DeprecationWarning, match=DEPRECATED_STR):
        assert curl.getinfo(pycurl.SPEED_DOWNLOAD) > 0
    with pytest.warns(DeprecationWarning, match=DEPRECATED_STR):
        assert 7 == curl.getinfo(pycurl.SIZE_DOWNLOAD)
    assert f"{app}/success" == curl.getinfo(pycurl.EFFECTIVE_URL)
    assert "text/html; charset=utf-8" == curl.getinfo(pycurl.CONTENT_TYPE).lower()
    assert type(curl.getinfo(pycurl.NAMELOOKUP_TIME)) is float
    assert curl.getinfo(pycurl.NAMELOOKUP_TIME) > 0
    assert curl.getinfo(pycurl.NAMELOOKUP_TIME) < 1
    assert 0 == curl.getinfo(pycurl.REDIRECT_TIME)
    assert 0 == curl.getinfo(pycurl.REDIRECT_COUNT)
    # time not requested
    assert -1 == curl.getinfo(pycurl.INFO_FILETIME)

@util.min_libcurl(7, 72, 0)
def test_getinfo_effective_method(curl, app):
    make_request(curl, app)
    assert "GET" == curl.getinfo(pycurl.EFFECTIVE_METHOD)

@flaky.flaky(max_runs=3)
def test_getinfo_times(curl, app):
    make_request(curl, app)

    assert 200 == curl.getinfo(pycurl.HTTP_CODE)
    assert 200 == curl.getinfo(pycurl.RESPONSE_CODE)
    assert type(curl.getinfo(pycurl.TOTAL_TIME)) is float
    assert curl.getinfo(pycurl.TOTAL_TIME) > 0
    assert curl.getinfo(pycurl.TOTAL_TIME) < 1

@util.min_libcurl(7, 21, 0)
def test_primary_port_etc(curl, app):
    make_request(curl, app)
    assert type(curl.getinfo(pycurl.PRIMARY_PORT)) is int
    assert type(curl.getinfo(pycurl.LOCAL_IP)) is str
    assert type(curl.getinfo(pycurl.LOCAL_PORT)) is int

def make_request(curl, app, path="/success", expected_body="success"):
    curl.setopt(pycurl.URL, f"{app}{path}")
    sio = BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    curl.perform()
    assert expected_body == sio.getvalue().decode()

def test_getinfo_cookie_invalid_utf8(curl, app):
    curl.setopt(curl.COOKIELIST, "")
    make_request(curl, app, "/set_cookie_invalid_utf8", "cookie set")

    assert 200 == curl.getinfo(pycurl.HTTP_CODE)

    info = curl.getinfo(pycurl.INFO_COOKIELIST)
    domain, incl_subdomains, path, secure, expires, name, value = info[0].split("\t")
    assert "\xb3\xd2\xda\xcd\xd7" == name

@pytest.mark.skip(reason="bottle converts to utf-8? try without it")
def test_getinfo_raw_cookie_invalid_utf8(curl, app):

    curl.setopt(curl.COOKIELIST, "")
    make_request(curl, app, "/set_cookie_invalid_utf8", "cookie set")

    assert 200 == curl.getinfo(pycurl.HTTP_CODE)
    expected = util.b(f"{localhost}\tFALSE\t/\tFALSE\t0\t\xb3\xd2\xda\xcd\xd7\t%96%A6g%9Ay%B0%A5g%A7tm%7C%95%9A")
    assert [expected] == curl.getinfo_raw(pycurl.INFO_COOKIELIST)

def test_getinfo_content_type_invalid_utf8(curl, app):
    make_request(curl, app, "/content_type_invalid_utf8", "content type set")

    assert 200 == curl.getinfo(pycurl.HTTP_CODE)

    value = curl.getinfo(pycurl.CONTENT_TYPE)
    assert "\xb3\xd2\xda\xcd\xd7" == value

@pytest.mark.skip(reason="bottle converts to utf-8? try without it")
def test_getinfo_raw_content_type_invalid_utf8(curl, app):
    make_request(curl, app, "/content_type_invalid_utf8", "content type set")

    assert 200 == curl.getinfo(pycurl.HTTP_CODE)
    expected = util.b("\xb3\xd2\xda\xcd\xd7")
    assert expected == curl.getinfo_raw(pycurl.CONTENT_TYPE)

def test_getinfo_number(curl, app):
    make_request(curl, app)
    with pytest.warns(DeprecationWarning, match=DEPRECATED_STR):
        assert 7 == curl.getinfo(pycurl.SIZE_DOWNLOAD)

def test_getinfo_raw_number(curl, app):
    make_request(curl, app)
    with pytest.warns(DeprecationWarning, match=DEPRECATED_STR):
        assert 7 == curl.getinfo_raw(pycurl.SIZE_DOWNLOAD)

@util.min_libcurl(7, 55, 0)
def test_getinfo_upload_download_t(curl, app):
    make_request(curl, app)
    assert 7 == curl.getinfo(pycurl.SIZE_DOWNLOAD_T)
    assert type(curl.getinfo(pycurl.CONTENT_LENGTH_DOWNLOAD_T)) is int
    assert type(curl.getinfo(pycurl.CONTENT_LENGTH_UPLOAD_T)) is int
    assert type(curl.getinfo(pycurl.SIZE_DOWNLOAD_T)) is int
    assert type(curl.getinfo(pycurl.SIZE_UPLOAD_T)) is int
    assert type(curl.getinfo(pycurl.SPEED_DOWNLOAD_T)) is int
    assert type(curl.getinfo(pycurl.SPEED_UPLOAD_T)) is int

@util.min_libcurl(7, 59, 0)
def test_getinfo_filetime_t(curl, app):
    make_request(curl, app)
    assert type(curl.getinfo(pycurl.FILETIME_T)) is int

@util.min_libcurl(7, 61, 0)
def test_getinfo_connect_transfer_t(curl, app):
    make_request(curl, app)
    assert type(curl.getinfo(pycurl.APPCONNECT_TIME_T)) is int
    assert type(curl.getinfo(pycurl.CONNECT_TIME_T)) is int
    assert type(curl.getinfo(pycurl.NAMELOOKUP_TIME_T)) is int
    assert type(curl.getinfo(pycurl.PRETRANSFER_TIME_T)) is int
    assert type(curl.getinfo(pycurl.REDIRECT_TIME_T)) is int
    assert type(curl.getinfo(pycurl.STARTTRANSFER_TIME_T)) is int
    assert type(curl.getinfo(pycurl.TOTAL_TIME_T)) is int

@util.min_libcurl(8, 6, 0)
def test_getinfo_queue_time_t(curl, app):
    make_request(curl, app)
    assert type(curl.getinfo(pycurl.QUEUE_TIME_T)) is int

@util.min_libcurl(8, 10, 0)
def test_getinfo_posttransfer_time_t(curl, app):
    make_request(curl, app)
    assert type(curl.getinfo(pycurl.POSTTRANSFER_TIME_T)) is int

@util.min_libcurl(8, 11, 0)
def test_getinfo_earlydata_sent_t(curl, app):
    make_request(curl, app)
    assert type(curl.getinfo(pycurl.EARLYDATA_SENT_T)) is int

@util.min_libcurl(7, 45, 0)
def test_active_socket(curl, app):
    curl.setopt(pycurl.FORBID_REUSE, False)
    curl.setopt(pycurl.CONNECT_ONLY, True)
    socket = curl.getinfo(pycurl.ACTIVESOCKET)
    assert socket == -1
    assert socket == curl.getinfo(pycurl.LASTSOCKET)
    curl.setopt(pycurl.URL, app)
    curl.perform()
    socket = curl.getinfo(pycurl.ACTIVESOCKET)
    assert socket != -1
    assert socket == curl.getinfo(pycurl.LASTSOCKET)

@pytest.mark.parametrize(
    "option",
    [
        pycurl.CONTENT_LENGTH_DOWNLOAD,
        pycurl.CONTENT_LENGTH_UPLOAD,
    ],
)
def test_deprecated_getinfo_options(curl, app, option):
    make_request(curl, app)
    with pytest.warns(DeprecationWarning, match=DEPRECATED_STR):
        curl.getinfo(option)
