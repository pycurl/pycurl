import warnings

import pytest

import pycurl

from . import util

pytestmark = pytest.mark.skipif(
    util.pycurl_version_less_than(7, 32, 0), reason="libcurl < 7.32.0"
)


@pytest.fixture
def xferinfo_curl(curl, app):
    curl.setopt(pycurl.URL, f"{app}/long_pause")
    curl.setopt(pycurl.NOPROGRESS, False)
    return curl


def test_xferinfo_cb(xferinfo_curl):
    all_args = []

    def xferinfofunction(*args):
        all_args.append(args)

    xferinfo_curl.setopt(pycurl.XFERINFOFUNCTION, xferinfofunction)

    xferinfo_curl.perform()
    assert len(all_args) > 0
    for args in all_args:
        assert len(args) == 4
        for arg in args:
            assert isinstance(arg, int)


PROGRESS_OPTIONS = [
    pytest.param(pycurl.XFERINFOFUNCTION, "xferinfo", id="xferinfo"),
    pytest.param(pycurl.PROGRESSFUNCTION, "progress", id="progress"),
]


def _assert_aborts(curl, option, return_value):
    called = []

    def progressfunction(*args):
        called.append(True)
        return return_value

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        curl.setopt(option, progressfunction)

    with pytest.raises(pycurl.error) as exc_info:
        curl.perform()
    assert exc_info.value.args[0] == pycurl.E_ABORTED_BY_CALLBACK
    assert called


@pytest.mark.parametrize("return_value", [-1, 1], ids=["negative", "one"])
def test_xferinfo_nonzero_return_aborts(xferinfo_curl, return_value):
    _assert_aborts(xferinfo_curl, pycurl.XFERINFOFUNCTION, return_value)


@pytest.mark.parametrize("option, callback_name", PROGRESS_OPTIONS)
@pytest.mark.parametrize(
    "return_value",
    [2**31, 2**32, 2**70],
    ids=["int32-overflow", "int-truncates-to-zero", "long-overflow"],
)
def test_progress_oversized_return_aborts(
    xferinfo_curl, option, callback_name, return_value, capfd
):
    _assert_aborts(xferinfo_curl, option, return_value)
    assert (
        f"OverflowError: {callback_name} callback returned {return_value} "
        "which does not fit in an int"
    ) in capfd.readouterr().err


def test_xferinfo_exception_aborts(xferinfo_curl):
    called = []

    def xferinfofunction(*args):
        called.append(True)
        raise ValueError

    xferinfo_curl.setopt(pycurl.XFERINFOFUNCTION, xferinfofunction)

    with pytest.raises(pycurl.error) as exc_info:
        xferinfo_curl.perform()
    assert exc_info.value.args[0] == pycurl.E_ABORTED_BY_CALLBACK
    assert called
