import sys

import pycurl
import pytest

from . import util


def _no_op_read():
    return None


def _no_op_write(entry, index):
    return pycurl.CURLSTS_OK


@util.min_libcurl(7, 74, 0)
def test_hsts_file_path_setopt_and_unset(curl, tmp_path):
    cache = tmp_path / "hsts.cache"
    curl.setopt(pycurl.HSTS, str(cache))
    curl.unsetopt(pycurl.HSTS)


@util.min_libcurl(7, 74, 0)
def test_hsts_ctrl_setopt(curl):
    curl.setopt(pycurl.HSTS_CTRL, pycurl.CURLHSTS_ENABLE)


@util.min_libcurl(7, 74, 0)
def test_hstsread_setopt_and_unset(curl):
    curl.setopt(pycurl.HSTSREADFUNCTION, _no_op_read)
    curl.unsetopt(pycurl.HSTSREADFUNCTION)


@util.min_libcurl(7, 74, 0)
def test_hstswrite_setopt_and_unset(curl):
    curl.setopt(pycurl.HSTSWRITEFUNCTION, _no_op_write)
    curl.unsetopt(pycurl.HSTSWRITEFUNCTION)


@util.min_libcurl(7, 74, 0)
def test_hstsread_rejects_noncallable(curl):
    with pytest.raises(TypeError):
        curl.setopt(pycurl.HSTSREADFUNCTION, 42)


@util.min_libcurl(7, 74, 0)
def test_hstswrite_rejects_noncallable(curl):
    with pytest.raises(TypeError):
        curl.setopt(pycurl.HSTSWRITEFUNCTION, 42)


@util.min_libcurl(7, 74, 0)
def test_hstsread_set_none_unsets(curl):
    curl.setopt(pycurl.HSTSREADFUNCTION, _no_op_read)
    curl.setopt(pycurl.HSTSREADFUNCTION, None)


@util.min_libcurl(7, 74, 0)
def test_hstswrite_set_none_unsets(curl):
    curl.setopt(pycurl.HSTSWRITEFUNCTION, _no_op_write)
    curl.setopt(pycurl.HSTSWRITEFUNCTION, None)


@util.min_libcurl(7, 74, 0)
def test_hsts_entry_and_index_are_namedtuples():
    entry = pycurl.HstsEntry(host=b"example.com", expire=None, include_subdomains=True)
    assert entry.host == b"example.com"
    assert entry.expire is None
    assert entry.include_subdomains is True
    assert entry == (b"example.com", None, True)

    index = pycurl.HstsIndex(index=0, total=1)
    assert index.index == 0
    assert index.total == 1
    assert index == (0, 1)


@util.min_libcurl(7, 74, 0)
def test_hstsread_replace_refcount(curl):
    before = sys.getrefcount(_no_op_read)
    curl.setopt(pycurl.HSTSREADFUNCTION, _no_op_read)
    curl.setopt(pycurl.HSTSREADFUNCTION, lambda: None)
    assert sys.getrefcount(_no_op_read) == before


@util.min_libcurl(7, 74, 0)
def test_hstswrite_replace_refcount(curl):
    before = sys.getrefcount(_no_op_write)
    curl.setopt(pycurl.HSTSWRITEFUNCTION, _no_op_write)
    curl.setopt(pycurl.HSTSWRITEFUNCTION, lambda entry, index: pycurl.CURLSTS_OK)
    assert sys.getrefcount(_no_op_write) == before
