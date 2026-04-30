from io import BytesIO
from pathlib import Path

import pycurl
import pytest

from . import util


@util.only_ssl_backends("openssl")
def test_request_with_verifypeer(ssl_curl, ssl_app):
    cert_path = Path(__file__).parent / "certs" / "ca.crt"
    cadata = cert_path.read_bytes().decode("ASCII")

    ssl_curl.setopt(pycurl.URL, f"{ssl_app}/success")
    sio = BytesIO()
    ssl_curl.set_ca_certs(cadata)
    ssl_curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    # self signed certificate, but ca cert should be loaded
    ssl_curl.setopt(pycurl.SSL_VERIFYPEER, 1)
    ssl_curl.perform()
    assert sio.getvalue().decode() == "success"


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
