import sys

import pycurl
import pytest

from . import util


def _no_trailers():
    return None


def _some_trailers():
    return ["X-Test: v"]


@util.min_libcurl(7, 64, 0)
def test_trailer_setopt_and_unset(curl):
    curl.setopt(pycurl.TRAILERFUNCTION, _no_trailers)
    curl.unsetopt(pycurl.TRAILERFUNCTION)


@util.min_libcurl(7, 64, 0)
def test_trailer_replace_refcount(curl):
    before = sys.getrefcount(_no_trailers)
    curl.setopt(pycurl.TRAILERFUNCTION, _no_trailers)
    curl.setopt(pycurl.TRAILERFUNCTION, _some_trailers)
    assert sys.getrefcount(_no_trailers) == before


@util.min_libcurl(7, 64, 0)
def test_trailer_rejects_noncallable(curl):
    with pytest.raises(TypeError):
        curl.setopt(pycurl.TRAILERFUNCTION, 42)


@util.min_libcurl(7, 64, 0)
def test_trailer_set_none_unsets(curl):
    curl.setopt(pycurl.TRAILERFUNCTION, _some_trailers)
    curl.setopt(pycurl.TRAILERFUNCTION, None)
