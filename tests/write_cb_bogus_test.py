import sys
from pathlib import Path

import pycurl
import pytest


@pytest.mark.parametrize(
    "bogus_return",
    ["foo", 0.5],
    ids=["returning_string", "returning_float"],
)
def test_write_cb_bogus_return(curl, bogus_return):
    curl.setopt(pycurl.URL, Path(__file__).resolve().as_uri())
    curl.setopt(pycurl.WRITEFUNCTION, lambda _: bogus_return)

    with pytest.raises(pycurl.error) as exc_info:
        curl.perform()
    assert exc_info.value.args[0] == pycurl.E_WRITE_ERROR

    assert hasattr(sys, "last_type")
    assert sys.last_type == pycurl.error
    assert hasattr(sys, "last_value")
    assert str(sys.last_value) == "write callback must return int or None"
