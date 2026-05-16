import sys
from pathlib import Path

import pycurl
import pytest


def test_write_abort(curl):
    try:
        del sys.last_value
    except AttributeError:
        pass

    curl.setopt(pycurl.URL, Path(__file__).resolve().as_uri())
    curl.setopt(pycurl.WRITEFUNCTION, lambda _: -1)

    with pytest.raises(pycurl.error) as exc_info:
        curl.perform()
    assert exc_info.value.args[0] == pycurl.E_WRITE_ERROR

    # no additional errors should be reported
    assert not hasattr(sys, "last_value")
