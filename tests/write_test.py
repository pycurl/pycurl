import pycurl
import pytest


class Acceptor:
    def __init__(self):
        self.buffer = ""

    def write(self, chunk):
        self.buffer += chunk.decode()


def test_write_to_tempfile_via_function(curl, app, tmp_path):
    curl.setopt(pycurl.URL, f"{app}/success")
    with (tmp_path / "out").open("wb+") as f:
        curl.setopt(pycurl.WRITEFUNCTION, f.write)
        curl.perform()
        f.seek(0)
        assert f.read().decode() == "success"


def test_write_to_tempfile_via_object(curl, app, tmp_path):
    curl.setopt(pycurl.URL, f"{app}/success")
    with (tmp_path / "out").open("wb+") as f:
        curl.setopt(pycurl.WRITEDATA, f)
        curl.perform()
        f.seek(0)
        assert f.read().decode() == "success"


def test_write_to_file_via_function(curl, app, tmp_path):
    curl.setopt(pycurl.URL, f"{app}/success")
    with (tmp_path / "pycurltest").open("wb+") as f:
        curl.setopt(pycurl.WRITEFUNCTION, f.write)
        curl.perform()
        f.seek(0)
        assert f.read().decode() == "success"


def test_write_to_file_via_object(curl, app, tmp_path):
    curl.setopt(pycurl.URL, f"{app}/success")
    with (tmp_path / "pycurltest").open("wb+") as f:
        curl.setopt(pycurl.WRITEDATA, f)
        curl.perform()
        f.seek(0)
        assert f.read().decode() == "success"


def test_write_to_file_like(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    acceptor = Acceptor()
    curl.setopt(pycurl.WRITEDATA, acceptor)
    curl.perform()
    assert acceptor.buffer == "success"


def test_write_to_file_like_then_real_file(curl, app, tmp_path):
    curl.setopt(pycurl.URL, f"{app}/success")
    acceptor = Acceptor()
    curl.setopt(pycurl.WRITEDATA, acceptor)
    curl.perform()
    assert acceptor.buffer == "success"

    with (tmp_path / "out").open("wb+") as real_f:
        curl.setopt(pycurl.WRITEDATA, real_f)
        curl.perform()
        real_f.seek(0)
        assert real_f.read().decode() == "success"


def test_headerfunction_and_writefunction(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    header_acceptor = Acceptor()
    body_acceptor = Acceptor()
    curl.setopt(pycurl.HEADERFUNCTION, header_acceptor.write)
    curl.setopt(pycurl.WRITEFUNCTION, body_acceptor.write)
    curl.perform()
    assert body_acceptor.buffer == "success"
    assert "content-type" in header_acceptor.buffer.lower()


def test_writeheader_and_writedata_file_like(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    header_acceptor = Acceptor()
    body_acceptor = Acceptor()
    curl.setopt(pycurl.WRITEHEADER, header_acceptor)
    curl.setopt(pycurl.WRITEDATA, body_acceptor)
    curl.perform()
    assert body_acceptor.buffer == "success"
    assert "content-type" in header_acceptor.buffer.lower()


def test_writeheader_and_writedata_real_file(curl, app, tmp_path):
    curl.setopt(pycurl.URL, f"{app}/success")
    with (
        (tmp_path / "header").open("wb+") as real_f_header,
        (tmp_path / "data").open("wb+") as real_f_data,
    ):
        curl.setopt(pycurl.WRITEHEADER, real_f_header)
        curl.setopt(pycurl.WRITEDATA, real_f_data)
        curl.perform()
        real_f_header.seek(0)
        real_f_data.seek(0)
        assert real_f_data.read().decode() == "success"
        assert "content-type" in real_f_header.read().decode().lower()


def test_writedata_and_writefunction_file_like(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    data_acceptor = Acceptor()
    function_acceptor = Acceptor()
    curl.setopt(pycurl.WRITEDATA, data_acceptor)
    curl.setopt(pycurl.WRITEFUNCTION, function_acceptor.write)
    curl.perform()
    assert data_acceptor.buffer == ""
    assert function_acceptor.buffer == "success"


def test_writedata_and_writefunction_real_file(curl, app, tmp_path):
    curl.setopt(pycurl.URL, f"{app}/success")
    function_acceptor = Acceptor()
    with (tmp_path / "out").open("wb+") as real_f:
        curl.setopt(pycurl.WRITEDATA, real_f)
        curl.setopt(pycurl.WRITEFUNCTION, function_acceptor.write)
        curl.perform()
        real_f.seek(0)
        assert real_f.read().decode().lower() == ""
    assert function_acceptor.buffer == "success"


def test_writefunction_and_writedata_file_like(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    data_acceptor = Acceptor()
    function_acceptor = Acceptor()
    curl.setopt(pycurl.WRITEFUNCTION, function_acceptor.write)
    curl.setopt(pycurl.WRITEDATA, data_acceptor)
    curl.perform()
    assert data_acceptor.buffer == "success"
    assert function_acceptor.buffer == ""


def test_writefunction_unsetopt(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    curl.setopt(pycurl.WRITEFUNCTION, None)
    curl.perform()
    # does not crash


def test_writefunction_and_writedata_real_file(curl, app, tmp_path):
    curl.setopt(pycurl.URL, f"{app}/success")
    function_acceptor = Acceptor()
    with (tmp_path / "out").open("wb+") as real_f:
        curl.setopt(pycurl.WRITEFUNCTION, function_acceptor.write)
        curl.setopt(pycurl.WRITEDATA, real_f)
        curl.perform()
        real_f.seek(0)
        assert real_f.read().decode().lower() == "success"
    assert function_acceptor.buffer == ""


def test_writeheader_and_headerfunction_file_like(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    data_acceptor = Acceptor()
    function_acceptor = Acceptor()
    body_acceptor = Acceptor()
    curl.setopt(pycurl.WRITEHEADER, data_acceptor)
    curl.setopt(pycurl.HEADERFUNCTION, function_acceptor.write)
    # silence output
    curl.setopt(pycurl.WRITEDATA, body_acceptor)
    curl.perform()
    assert data_acceptor.buffer == ""
    assert "content-type" in function_acceptor.buffer.lower()


def test_writeheader_and_headerfunction_real_file(curl, app, tmp_path):
    curl.setopt(pycurl.URL, f"{app}/success")
    function_acceptor = Acceptor()
    body_acceptor = Acceptor()
    with (tmp_path / "out").open("wb+") as real_f:
        curl.setopt(pycurl.WRITEHEADER, real_f)
        curl.setopt(pycurl.HEADERFUNCTION, function_acceptor.write)
        # silence output
        curl.setopt(pycurl.WRITEDATA, body_acceptor)
        curl.perform()
        real_f.seek(0)
        assert real_f.read().decode().lower() == ""
    assert "content-type" in function_acceptor.buffer.lower()


def test_headerfunction_and_writeheader_file_like(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    data_acceptor = Acceptor()
    function_acceptor = Acceptor()
    body_acceptor = Acceptor()
    curl.setopt(pycurl.HEADERFUNCTION, function_acceptor.write)
    curl.setopt(pycurl.WRITEHEADER, data_acceptor)
    # silence output
    curl.setopt(pycurl.WRITEDATA, body_acceptor)
    curl.perform()
    assert "content-type" in data_acceptor.buffer.lower()
    assert function_acceptor.buffer == ""


def test_headerfunction_and_writeheader_real_file(curl, app, tmp_path):
    curl.setopt(pycurl.URL, f"{app}/success")
    function_acceptor = Acceptor()
    body_acceptor = Acceptor()
    with (tmp_path / "out").open("wb+") as real_f:
        curl.setopt(pycurl.HEADERFUNCTION, function_acceptor.write)
        curl.setopt(pycurl.WRITEHEADER, real_f)
        # silence output
        curl.setopt(pycurl.WRITEDATA, body_acceptor)
        curl.perform()
        real_f.seek(0)
        assert "content-type" in real_f.read().decode().lower()
    assert function_acceptor.buffer == ""


def test_writedata_not_file_like(curl):
    with pytest.raises(TypeError, match="object given without a write method"):
        curl.setopt(curl.WRITEDATA, object())


def test_writeheader_not_file_like(curl):
    with pytest.raises(TypeError, match="object given without a write method"):
        curl.setopt(curl.WRITEHEADER, object())
