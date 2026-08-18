import gc
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import pycurl
import pytest

from . import util


def _ca_cert_data():
    return (Path(__file__).parent / "certs" / "ca.crt").read_bytes().decode("ASCII")


def _fetch_success(curl, url):
    sio = BytesIO()
    curl.setopt(pycurl.URL, url)
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    curl.perform()
    return sio.getvalue().decode()


@util.only_ssl_backends("openssl")
def test_request_with_verifypeer(ssl_curl, ssl_app):
    ssl_curl.set_ca_certs(_ca_cert_data())
    # self signed certificate, but ca cert should be loaded
    ssl_curl.setopt(pycurl.SSL_VERIFYPEER, 1)
    assert _fetch_success(ssl_curl, f"{ssl_app}/success") == "success"


@util.only_ssl_backends("openssl")
def test_set_ca_certs_bytes(curl):
    curl.set_ca_certs(util.b("hello world\x02\xe0"))


@util.only_ssl_backends("openssl")
def test_set_ca_certs_bogus_type(curl):
    with pytest.raises(TypeError) as exc_info:
        curl.set_ca_certs(42)
    assert (
        str(exc_info.value)
        == "set_ca_certs argument must be a byte string or a Unicode string with ASCII code points only"
    )


@util.only_ssl_backends("openssl")
def test_set_ca_certs_without_a_certificate_reports_an_error(ssl_curl, ssl_app):
    ssl_curl.set_ca_certs("this blob holds no certificate")
    ssl_curl.setopt(pycurl.SSL_VERIFYPEER, 1)
    ssl_curl.setopt(pycurl.URL, f"{ssl_app}/success")

    # the ssl ctx callback reports its failure as E_FAILED_INIT, so the parse
    # error itself only reaches stderr
    with pytest.raises(pycurl.error) as exc_info:
        ssl_curl.perform()
    assert exc_info.value.args[0] == pycurl.E_FAILED_INIT


@pytest.mark.parametrize("free_original", [False, True], ids=["alive", "freed"])
@util.only_ssl_backends("openssl")
def test_duphandle_keeps_ca_certs_working(ssl_app, free_original):
    orig = util.DefaultCurlLocalhost(urlparse(ssl_app).port)
    orig.set_ca_certs(_ca_cert_data())
    orig.setopt(pycurl.SSL_VERIFYPEER, 1)

    dup = orig.duphandle()
    try:
        if free_original:
            orig.close()
            orig = None
            gc.collect()
        assert _fetch_success(dup, f"{ssl_app}/success") == "success"
    finally:
        dup.close()
        if orig is not None:
            orig.close()
