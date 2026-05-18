import sys

import pycurl
import pytest


@pytest.fixture(
    params=[pycurl.WRITEFUNCTION, pycurl.HEADERFUNCTION],
    ids=["write", "header"],
)
def cb_option(request):
    return request.param


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"use_memoryview": False}],
    ids=["default", "use_memoryview_false"],
)
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


def test_memoryview_true_passes_readonly_memoryview(curl, app, cb_option):
    curl.setopt(pycurl.URL, f"{app}/success")
    seen = []

    def cb(chunk):
        seen.append((type(chunk), chunk.readonly))
        return len(chunk)

    curl.setopt(cb_option, cb, use_memoryview=True)
    curl.perform()
    assert seen
    for typ, readonly in seen:
        assert typ is memoryview
        assert readonly is True


def test_memoryview_true_return_none(curl, app, cb_option):
    curl.setopt(pycurl.URL, f"{app}/success")
    chunks = []
    curl.setopt(
        cb_option, lambda chunk: chunks.append(bytes(chunk)), use_memoryview=True
    )
    curl.perform()
    assert b"".join(chunks)  # got data


def test_memoryview_true_return_length(curl, app, cb_option):
    curl.setopt(pycurl.URL, f"{app}/success")
    curl.setopt(cb_option, lambda chunk: len(chunk), use_memoryview=True)
    curl.perform()  # would raise if length mismatched


def test_memoryview_true_wrong_length_aborts(curl, app, cb_option):
    curl.setopt(pycurl.URL, f"{app}/success")
    curl.setopt(
        cb_option, lambda chunk: 1 if len(chunk) > 1 else 0, use_memoryview=True
    )
    with pytest.raises(pycurl.error) as exc_info:
        curl.perform()
    assert exc_info.value.args[0] == pycurl.E_WRITE_ERROR


def test_memoryview_true_callback_exception_preserved(curl, app, cb_option):
    curl.setopt(pycurl.URL, f"{app}/success")

    def cb(_):
        raise RuntimeError("boom")

    curl.setopt(cb_option, cb, use_memoryview=True)
    with pytest.raises(pycurl.error) as exc_info:
        curl.perform()
    assert exc_info.value.args[0] == pycurl.E_WRITE_ERROR
    assert sys.last_type is RuntimeError
    assert str(sys.last_value) == "boom"


def test_memoryview_released_after_callback(curl, app, cb_option):
    curl.setopt(pycurl.URL, f"{app}/success")
    stashed = []

    def cb(chunk):
        stashed.append(chunk)
        return len(chunk)

    curl.setopt(cb_option, cb, use_memoryview=True)
    curl.perform()
    assert stashed
    with pytest.raises(ValueError, match="released memoryview"):
        bytes(stashed[0])


def test_setopt_without_memoryview_resets_to_bytes(curl, app, cb_option):
    curl.setopt(pycurl.URL, f"{app}/success")
    seen = []

    def cb(chunk):
        seen.append(type(chunk))
        return len(chunk)

    curl.setopt(cb_option, cb, use_memoryview=True)
    curl.setopt(cb_option, cb)  # no memoryview kwarg -> reset to default
    curl.perform()
    assert seen
    assert all(t is bytes for t in seen)


def test_duphandle_preserves_memoryview_flag(curl, app, cb_option):
    curl.setopt(pycurl.URL, f"{app}/success")
    seen = []

    def cb(chunk):
        seen.append(type(chunk))
        return len(chunk)

    curl.setopt(cb_option, cb, use_memoryview=True)
    dup = curl.duphandle()
    try:
        dup.perform()
    finally:
        dup.close()
    assert seen
    assert all(t is memoryview for t in seen)


@pytest.mark.parametrize("flag", [False, True])
def test_memoryview_rejected_on_unrelated_option(curl, app, flag):
    with pytest.raises(
        TypeError,
        match="use_memoryview is only supported for WRITEFUNCTION and HEADERFUNCTION",
    ):
        curl.setopt(pycurl.URL, f"{app}/success", use_memoryview=flag)


def test_memoryview_must_be_keyword_only(curl):
    with pytest.raises(TypeError):
        curl.setopt(pycurl.WRITEFUNCTION, lambda chunk: len(chunk), True)
