from io import BytesIO

import pycurl
import pytest


def test_reset_preserves_default_useragent(app, curl):
    curl.setopt(pycurl.USERAGENT, "Phony/42")
    curl.setopt(pycurl.URL, f"{app}/header?h=user-agent")
    sio = BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    curl.perform()
    assert sio.getvalue().decode() == "Phony/42"

    curl.reset()
    curl.setopt(pycurl.URL, f"{app}/header?h=user-agent")
    sio = BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    curl.perform()
    assert sio.getvalue().decode().startswith("PycURL")


def test_reset_after_close_raises():
    c = pycurl.Curl()
    c.close()
    with pytest.raises(pycurl.error):
        c.reset()
