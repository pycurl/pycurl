import pytest

import pycurl

from . import util


@pytest.fixture
def sockopt_curl(curl, app):
    curl.setopt(pycurl.URL, f"{app}/success")
    return curl


def _record_and_return(called, value):
    def sockoptfunction(curlfd, purpose):
        called.append(True)
        return value

    return sockoptfunction


def test_sockoptfunction_ok(sockopt_curl):
    called = []
    sockopt_curl.setopt(pycurl.SOCKOPTFUNCTION, _record_and_return(called, 0))

    sockopt_curl.perform()
    assert called


def _assert_connection_refused(curl, return_value):
    called = []
    curl.setopt(pycurl.SOCKOPTFUNCTION, _record_and_return(called, return_value))

    with pytest.raises(pycurl.error) as exc_info:
        curl.perform()
    assert exc_info.value.args[0] in (
        pycurl.E_ABORTED_BY_CALLBACK,
        pycurl.E_COULDNT_CONNECT,
    )
    assert called


def test_sockoptfunction_fail(sockopt_curl):
    _assert_connection_refused(sockopt_curl, 1)


class _UnreprableReturn:
    def __repr__(self):
        raise ValueError("no repr")


@pytest.mark.parametrize(
    "return_value, expected",
    [
        ("bogus", "returned 'bogus' which is not an integer"),
        # the repr is encoded with backslashreplace, so non-ASCII still prints
        ("caf\xe9", "returned 'caf\\xe9' which is not an integer"),
        (object(), "returned <object object at"),
        (_UnreprableReturn(), "returned a value which is not an integer"),
    ],
    ids=["ascii-str", "non-ascii-str", "object", "repr-raises"],
)
def test_sockoptfunction_bogus_return(sockopt_curl, return_value, expected, capfd):
    _assert_connection_refused(sockopt_curl, return_value)
    assert f"sockopt callback {expected}" in capfd.readouterr().err


@pytest.mark.parametrize(
    "return_value",
    [2**31, 2**32, 2**70],
    ids=["int32-overflow", "int-truncates-to-zero", "long-overflow"],
)
def test_sockoptfunction_oversized_return(sockopt_curl, return_value):
    called = []
    sockopt_curl.setopt(
        pycurl.SOCKOPTFUNCTION, _record_and_return(called, return_value)
    )

    with pytest.raises(OverflowError) as exc_info:
        sockopt_curl.perform()
    assert (
        str(exc_info.value)
        == f"sockopt callback returned {return_value} which does not fit in an int"
    )
    assert called


@util.min_libcurl(7, 28, 0)
def test_socktype_accept(curl):
    assert hasattr(pycurl, "SOCKTYPE_ACCEPT")
    assert hasattr(curl, "SOCKTYPE_ACCEPT")


def test_socktype_ipcxn(curl):
    assert hasattr(pycurl, "SOCKTYPE_IPCXN")
    assert hasattr(curl, "SOCKTYPE_IPCXN")


def test_sockoptfunction_none(curl):
    curl.setopt(pycurl.SOCKOPTFUNCTION, None)


def test_sockoptfunction_unset(curl):
    curl.unsetopt(pycurl.SOCKOPTFUNCTION)
