import sys

import pycurl
import pytest

from . import util


def _match(pattern, string):
    return pycurl.FNMATCHFUNC_MATCH


def _nomatch(pattern, string):
    return pycurl.FNMATCHFUNC_NOMATCH


@util.min_libcurl(7, 21, 0)
def test_fnmatch_setopt_and_unset(curl):
    curl.setopt(pycurl.FNMATCH_FUNCTION, _match)
    curl.unsetopt(pycurl.FNMATCH_FUNCTION)


@util.min_libcurl(7, 21, 0)
def test_fnmatch_replace_refcount(curl):
    before = sys.getrefcount(_match)
    curl.setopt(pycurl.FNMATCH_FUNCTION, _match)
    curl.setopt(pycurl.FNMATCH_FUNCTION, _nomatch)
    assert sys.getrefcount(_match) == before


@util.min_libcurl(7, 21, 0)
def test_fnmatch_rejects_noncallable(curl):
    with pytest.raises(TypeError):
        curl.setopt(pycurl.FNMATCH_FUNCTION, 42)
