from io import BytesIO

import pycurl
import pytest

from . import util


@util.min_libcurl(7, 19, 1)
def test_certinfo_option():
    assert hasattr(pycurl, "OPT_CERTINFO")


@util.min_libcurl(7, 19, 1)
@util.only_ssl
def test_request_without_certinfo(ssl_curl, ssl_app):
    ssl_curl.setopt(pycurl.URL, f"{ssl_app}/success")
    sio = BytesIO()
    ssl_curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    # self signed certificate
    ssl_curl.setopt(pycurl.SSL_VERIFYPEER, 0)
    ssl_curl.perform()
    assert sio.getvalue().decode() == "success"

    certinfo = ssl_curl.getinfo(pycurl.INFO_CERTINFO)
    assert certinfo == []


@pytest.mark.parametrize(
    "getter,coerce",
    [
        (pycurl.Curl.getinfo, util.u),
        (pycurl.Curl.getinfo_raw, util.b),
    ],
    ids=["getinfo", "getinfo_raw"],
)
@util.min_libcurl(7, 19, 1)
@util.only_ssl_backends("openssl")
def test_certinfo_returns_subject(ssl_curl, ssl_app, getter, coerce):
    ssl_curl.setopt(pycurl.URL, f"{ssl_app}/success")
    sio = BytesIO()
    ssl_curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    ssl_curl.setopt(pycurl.OPT_CERTINFO, 1)
    # self signed certificate
    ssl_curl.setopt(pycurl.SSL_VERIFYPEER, 0)
    ssl_curl.perform()
    assert sio.getvalue().decode() == "success"

    certinfo = getter(ssl_curl, pycurl.INFO_CERTINFO)
    # self signed certificate, one certificate in chain
    assert len(certinfo) == 1
    certinfo_dict = dict(certinfo[0])
    assert coerce("Subject") in certinfo_dict
    assert coerce("PycURL test suite") in certinfo_dict[coerce("Subject")]
