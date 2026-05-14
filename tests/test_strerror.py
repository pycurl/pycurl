import pytest

import pycurl

WRAPPERS = [
    pytest.param("easy_strerror", pycurl.E_OK, id="easy"),
    pytest.param("multi_strerror", pycurl.E_MULTI_OK, id="multi"),
    pytest.param("share_strerror", 0, id="share"),
    pytest.param(
        "url_strerror",
        0,
        id="url",
        marks=pytest.mark.skipif(
            not hasattr(pycurl, "url_strerror"),
            reason="libcurl < 7.80.0 — url_strerror not available",
        ),
    ),
]


@pytest.mark.parametrize("name,known_code", WRAPPERS)
def test_strerror_returns_non_empty_str(name, known_code):
    result = getattr(pycurl, name)(known_code)
    assert isinstance(result, str)
    assert result


@pytest.mark.parametrize("name,known_code", WRAPPERS)
def test_strerror_unknown_code_returns_str(name, known_code):
    result = getattr(pycurl, name)(99999)
    assert isinstance(result, str)
    assert result


@pytest.mark.parametrize("name,known_code", WRAPPERS)
def test_strerror_rejects_non_int(name, known_code):
    with pytest.raises(TypeError):
        getattr(pycurl, name)("not an int")
