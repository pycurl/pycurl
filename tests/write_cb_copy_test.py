import sys

import pycurl
import pytest


@pytest.fixture(
    params=[pycurl.WRITEFUNCTION, pycurl.HEADERFUNCTION],
    ids=["write", "header"],
)
def cb_option(request):
    return request.param


@pytest.mark.parametrize("kwargs", [{}, {"copy": True}], ids=["default", "copy_true"])
def test_passes_bytes(curl, app, cb_option, kwargs):
    curl.setopt(pycurl.URL, f"{app}/success")
    seen = []

    def cb(chunk):
        seen.append(type(chunk))
        return len(chunk)

    curl.setopt(cb_option, cb, **kwargs)
    curl.perform()
    assert seen
    assert all(t is bytes for t in seen)


def test_copy_false_passes_readonly_memoryview(curl, app, cb_option):
    curl.setopt(pycurl.URL, f"{app}/success")
    seen = []

    def cb(chunk):
        seen.append((type(chunk), chunk.readonly))
        return len(chunk)

    curl.setopt(cb_option, cb, copy=False)
    curl.perform()
    assert seen
    for typ, readonly in seen:
        assert typ is memoryview
        assert readonly is True


def test_copy_false_return_none(curl, app, cb_option):
    curl.setopt(pycurl.URL, f"{app}/success")
    chunks = []
    curl.setopt(cb_option, lambda chunk: chunks.append(bytes(chunk)), copy=False)
    curl.perform()
    assert b"".join(chunks)  # got data


def test_copy_false_return_length(curl, app, cb_option):
    curl.setopt(pycurl.URL, f"{app}/success")
    curl.setopt(cb_option, lambda chunk: len(chunk), copy=False)
    curl.perform()  # would raise if length mismatched


def test_copy_false_wrong_length_aborts(curl, app, cb_option):
    curl.setopt(pycurl.URL, f"{app}/success")
    curl.setopt(cb_option, lambda chunk: 1 if len(chunk) > 1 else 0, copy=False)
    with pytest.raises(pycurl.error) as exc_info:
        curl.perform()
    assert exc_info.value.args[0] == pycurl.E_WRITE_ERROR


def test_copy_false_callback_exception_preserved(curl, app, cb_option):
    curl.setopt(pycurl.URL, f"{app}/success")

    def cb(_):
        raise RuntimeError("boom")

    curl.setopt(cb_option, cb, copy=False)
    with pytest.raises(pycurl.error) as exc_info:
        curl.perform()
    assert exc_info.value.args[0] == pycurl.E_WRITE_ERROR
    assert sys.last_type is RuntimeError
    assert str(sys.last_value) == "boom"


def test_copy_false_memoryview_released_after_callback(curl, app, cb_option):
    curl.setopt(pycurl.URL, f"{app}/success")
    stashed = []

    def cb(chunk):
        stashed.append(chunk)
        return len(chunk)

    curl.setopt(cb_option, cb, copy=False)
    curl.perform()
    assert stashed
    with pytest.raises(ValueError, match="released memoryview"):
        bytes(stashed[0])


def test_setopt_without_copy_resets_to_bytes(curl, app, cb_option):
    curl.setopt(pycurl.URL, f"{app}/success")
    seen = []

    def cb(chunk):
        seen.append(type(chunk))
        return len(chunk)

    curl.setopt(cb_option, cb, copy=False)
    curl.setopt(cb_option, cb)  # no copy kwarg -> reset to default
    curl.perform()
    assert seen
    assert all(t is bytes for t in seen)


def test_duphandle_preserves_copy_flag(curl, app, cb_option):
    curl.setopt(pycurl.URL, f"{app}/success")
    seen = []

    def cb(chunk):
        seen.append(type(chunk))
        return len(chunk)

    curl.setopt(cb_option, cb, copy=False)
    dup = curl.duphandle()
    try:
        dup.perform()
    finally:
        dup.close()
    assert seen
    assert all(t is memoryview for t in seen)


@pytest.mark.parametrize("copy", [False, True])
def test_copy_rejected_on_unrelated_option(curl, app, copy):
    with pytest.raises(
        TypeError,
        match="copy is only supported for WRITEFUNCTION and HEADERFUNCTION",
    ):
        curl.setopt(pycurl.URL, f"{app}/success", copy=copy)


def test_copy_must_be_keyword_only(curl):
    with pytest.raises(TypeError):
        curl.setopt(pycurl.WRITEFUNCTION, lambda chunk: len(chunk), False)
