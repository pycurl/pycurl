import time as _time
from io import BytesIO

import pycurl


def test_get(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    sio = BytesIO()
    header_lines = []
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    curl.setopt(pycurl.HEADERFUNCTION, lambda line: header_lines.append(line.decode()))
    curl.perform()
    assert sio.getvalue().decode() == "success"

    assert len(header_lines) > 0
    assert header_lines[0] == "HTTP/1.0 200 OK\r\n"

    todays_day = _time.strftime("%a", _time.gmtime())
    for wanted in (
        f"Date: {todays_day}",
        "Server: WSGIServer",
        "Content-Length: 7",
        "Content-Type: text/html",
    ):
        assert any(wanted in line for line in header_lines), (
            f"{wanted!r} not found in {header_lines!r}"
        )
