import gc
import io
import json
import weakref

import pytest

import pycurl

pytestmark = pytest.mark.skipif(
    not hasattr(pycurl, "Mime"), reason="libcurl without MIME support"
)


def _make_tracking_mime(curl):
    class TrackingMime(pycurl.Mime):
        __slots__ = ("__weakref__",)

    return TrackingMime(curl)


def _perform_json(curl, url):
    response = io.BytesIO()
    curl.setopt(pycurl.URL, url)
    curl.setopt(pycurl.WRITEFUNCTION, response.write)
    curl.perform()
    return json.loads(response.getvalue().decode())


def _add_data_part(mime, helper_name, data_value):
    common_kwargs = {
        "content_type": "text/plain",
        "encoder": "binary",
        "headers": ["X-Test: yes"],
    }

    if helper_name == "add":
        return mime.add(
            name="field", data=data_value, filename="field.txt", **common_kwargs
        )
    if helper_name == "add_field":
        return mime.add_field("field", data_value, **common_kwargs)

    raise AssertionError(f"unknown helper_name: {helper_name}")


def _make_named_part(mime, name="field"):
    part = mime.addpart()
    part.name(name)
    return part


def _read_empty(_userdata, size):
    return b""


def _free_append_called(userdata):
    userdata.append("called")


class _ChunkReader:
    __slots__ = ("payload", "offset", "__weakref__")

    def __init__(self, payload=b"value"):
        self.payload = payload
        self.offset = 0

    def __call__(self, _userdata, size):
        if self.offset >= len(self.payload):
            return b""
        take = min(size, len(self.payload) - self.offset)
        chunk = self.payload[self.offset : self.offset + take]
        self.offset += len(chunk)
        return chunk


@pytest.fixture
def fixture_data_path(tmp_path):
    path = tmp_path / "fixture-data.bin"
    path.write_bytes(b"fixture-data")
    return path


@pytest.fixture(params=["bytes", "str", "memoryview"])
def data_value(request):
    if request.param == "bytes":
        return b"value"
    if request.param == "str":
        return "value"
    return memoryview(b"value")


def test_mime_lifecycle_and_context_manager():
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        assert mime.closed() is False

        mime.close()
        assert mime.closed() is True

        mime.close()
        assert mime.closed() is True

        with pycurl.Mime(curl) as second:
            assert second.closed() is False

        assert second.closed() is True


def test_mime_exit_requires_exception_tuple():
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        with pytest.raises(TypeError):
            mime.__exit__()


def test_mimepost_setopt_pins_mime_until_unset():
    curl = pycurl.Curl()
    try:
        mime = _make_tracking_mime(curl)
        mime.add_field("field", "value")

        mime_ref = weakref.ref(mime)
        curl.setopt(pycurl.MIMEPOST, mime)

        del mime
        gc.collect()
        assert mime_ref() is not None

        pinned_mime = mime_ref()
        assert pinned_mime is not None
        pinned_mime.add_field("extra", "value")

        curl.unsetopt(pycurl.MIMEPOST)
        del pinned_mime
        gc.collect()
        assert mime_ref() is None
    finally:
        curl.close()


def test_mimepost_setopt_requires_same_curl_handle():
    with pycurl.Curl() as curl1, pycurl.Curl() as curl2:
        mime = pycurl.Mime(curl1)
        with pytest.raises(ValueError, match="this Curl handle"):
            curl2.setopt(pycurl.MIMEPOST, mime)


def test_mimepost_setopt_rejects_attached_submime():
    with pycurl.Curl() as curl:
        parent = pycurl.Mime(curl)
        child = pycurl.Mime(curl)
        parent.addpart().subparts(child)

        with pytest.raises(ValueError, match="already attached as subparts"):
            curl.setopt(pycurl.MIMEPOST, child)


def test_mime_close_clears_mimepost_pin():
    curl = pycurl.Curl()
    try:
        mime = _make_tracking_mime(curl)
        mime.add_field("field", "value")
        curl.setopt(pycurl.MIMEPOST, mime)

        mime_ref = weakref.ref(mime)
        mime.close()
        del mime
        gc.collect()
        assert mime_ref() is None
    finally:
        curl.close()


def test_mimepost_replacement_keeps_new_pin():
    curl = pycurl.Curl()
    try:
        old_mime = _make_tracking_mime(curl)
        old_mime.add_field("old", "value")
        curl.setopt(pycurl.MIMEPOST, old_mime)

        old_ref = weakref.ref(old_mime)
        new_mime = _make_tracking_mime(curl)
        new_mime.add_field("new", "value")
        curl.setopt(pycurl.MIMEPOST, new_mime)

        del old_mime
        gc.collect()
        assert old_ref() is None

        new_ref = weakref.ref(new_mime)
        del new_mime
        gc.collect()
        assert new_ref() is not None

        curl.unsetopt(pycurl.MIMEPOST)
        gc.collect()
        assert new_ref() is None
    finally:
        curl.close()


def test_mime_data_cb_duphandle_free_called_once():
    curl = pycurl.Curl()
    dup = None
    try:
        mime = _make_tracking_mime(curl)
        part = _make_named_part(mime)

        free_calls = []
        part.data_cb(0, _read_empty, free=_free_append_called, userdata=free_calls)
        curl.setopt(pycurl.MIMEPOST, mime)
        dup = curl.duphandle()

        del part
        del mime
        gc.collect()

        curl.close()
        assert free_calls == []

        dup.close()
        gc.collect()
        assert free_calls == ["called"]
    finally:
        if dup is not None:
            dup.close()
        curl.close()


def test_mimepost_duphandle_supported_without_data_cb():
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        mime.add_field("field", "value")
        curl.setopt(pycurl.MIMEPOST, mime)

        dup = curl.duphandle()
        dup.close()


def test_mime_data_cb_replaced_by_data_then_duphandle_stays_single_free_call():
    curl = pycurl.Curl()
    dup = None
    try:
        mime = pycurl.Mime(curl)
        part = _make_named_part(mime)
        free_calls = []
        part.data_cb(0, _read_empty, free=_free_append_called, userdata=free_calls)
        part.data(b"value")
        assert free_calls == ["called"]

        curl.setopt(pycurl.MIMEPOST, mime)
        dup = curl.duphandle()
        curl.close()
        dup.close()
        gc.collect()
        assert free_calls == ["called"]
    finally:
        if dup is not None:
            dup.close()
        curl.close()


def test_mime_data_cb_replaced_after_duphandle_releases_each_owner_once():
    curl = pycurl.Curl()
    dup = None
    try:
        mime = pycurl.Mime(curl)
        part = _make_named_part(mime)
        old_calls = []
        new_calls = []

        part.data_cb(
            0,
            _read_empty,
            free=lambda userdata: userdata.append("old"),
            userdata=old_calls,
        )
        curl.setopt(pycurl.MIMEPOST, mime)
        dup = curl.duphandle()

        part.data_cb(
            0,
            _read_empty,
            free=lambda userdata: userdata.append("new"),
            userdata=new_calls,
        )

        curl.close()
        dup.close()
        mime.close()
        gc.collect()

        assert old_calls == ["old"]
        assert new_calls == ["new"]
    finally:
        if dup is not None:
            dup.close()
        curl.close()


def test_mime_data_cb_replaced_by_data_after_duphandle_calls_free_once():
    curl = pycurl.Curl()
    dup = None
    try:
        mime = pycurl.Mime(curl)
        part = _make_named_part(mime)
        old_calls = []

        part.data_cb(0, _read_empty, free=_free_append_called, userdata=old_calls)
        curl.setopt(pycurl.MIMEPOST, mime)
        dup = curl.duphandle()

        part.data(b"value")

        curl.close()
        dup.close()
        mime.close()
        gc.collect()

        assert old_calls == ["called"]
    finally:
        if dup is not None:
            dup.close()
        curl.close()


def test_mime_data_cb_owner_kept_alive_while_mimepost_is_set():
    curl = pycurl.Curl()
    dup = None
    try:
        mime = _make_tracking_mime(curl)
        part = _make_named_part(mime)
        reader = _ChunkReader(b"value")
        reader_ref = weakref.ref(reader)
        mime_ref = weakref.ref(mime)

        part.data_cb(5, reader)
        curl.setopt(pycurl.MIMEPOST, mime)
        dup = curl.duphandle()

        del part
        del reader
        del mime
        gc.collect()
        assert mime_ref() is not None
        assert reader_ref() is not None

        curl.close()
        gc.collect()
        assert reader_ref() is not None

        dup.close()
        gc.collect()
        assert mime_ref() is None
        assert reader_ref() is None
    finally:
        if dup is not None:
            dup.close()
        curl.close()


def test_mime_addpart_and_part_methods(fixture_data_path):
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        part = mime.addpart()
        assert isinstance(part, pycurl.MimePart)

        part.name("field")
        part.data(b"value")
        part.filename("value.txt")
        part.type("text/plain")
        part.encoder("binary")
        part.headers(["X-Test: yes"])
        part.filedata(str(fixture_data_path))

        mime.close()


def test_mimepart_data_accepts_common_value_types(data_value):
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        part = mime.addpart()
        part.data(data_value)


def test_mimepart_data_cb_streams_field_value(app):
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        part = mime.addpart()
        part.name("field")

        state = {"payload": b"value-from-data-cb", "offset": 0}

        def read_cb(userdata, size):
            assert userdata is state
            payload = userdata["payload"]
            offset = userdata["offset"]
            if offset >= len(payload):
                return b""
            take = min(4, size, len(payload) - offset)
            chunk = payload[offset : offset + take]
            userdata["offset"] = offset + len(chunk)
            return memoryview(chunk)

        part.data_cb(len(state["payload"]), read_cb, userdata=state)
        curl.setopt(pycurl.MIMEPOST, mime)

        assert _perform_json(curl, f"{app}/postfields") == {
            "field": state["payload"].decode()
        }


def test_mimepart_data_cb_requires_callable_read():
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        part = mime.addpart()

        with pytest.raises(TypeError, match="read must be callable"):
            part.data_cb(1, object())


def test_mimepart_data_cb_validates_seek_and_size():
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        part = mime.addpart()

        with pytest.raises(TypeError, match="seek must be callable or None"):
            part.data_cb(1, lambda _userdata, size: b"", seek=object())

        with pytest.raises(TypeError, match="free must be callable or None"):
            part.data_cb(1, lambda _userdata, size: b"", free=object())

        with pytest.raises(ValueError, match="datasize must be >= -1"):
            part.data_cb(-2, lambda _userdata, size: b"")


def test_mimepart_data_cb_bad_return_aborts_transfer(app):
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        part = _make_named_part(mime)

        def bad_read_cb(_userdata, size):
            return object()

        part.data_cb(5, bad_read_cb)
        curl.setopt(pycurl.MIMEPOST, mime)
        curl.setopt(pycurl.URL, f"{app}/postfields")

        with pytest.raises(pycurl.error) as exc_info:
            curl.perform()

        assert exc_info.value.args[0] == pycurl.E_ABORTED_BY_CALLBACK


def test_mimepart_data_cb_keeps_reader_alive_until_mime_close():
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        part = _make_named_part(mime)
        reader = _ChunkReader(b"value")
        reader_ref = weakref.ref(reader)
        part.data_cb(5, reader)

        del reader
        gc.collect()
        assert reader_ref() is not None

        mime.close()
        gc.collect()
        assert reader_ref() is None


def test_mimepart_data_cb_invokes_optional_free_callback():
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        part = _make_named_part(mime)

        called = []
        part.data_cb(0, _read_empty, free=_free_append_called, userdata=called)
        mime.close()

        assert called == ["called"]


def test_mimepart_data_cb_replaced_by_data_cb_releases_old_owner():
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        part = _make_named_part(mime)
        old_called = []
        new_called = []

        def free_old(userdata):
            userdata.append("old")

        def free_new(userdata):
            userdata.append("new")

        part.data_cb(0, _read_empty, free=free_old, userdata=old_called)
        part.data_cb(0, _read_empty, free=free_new, userdata=new_called)

        assert old_called == ["old"]
        mime.close()
        assert old_called == ["old"]
        assert new_called == ["new"]


@pytest.mark.parametrize("replacement_kind", ["data", "filedata", "subparts"])
def test_mimepart_data_cb_replaced_releases_old_owner(
    replacement_kind, fixture_data_path
):
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        part = _make_named_part(mime)
        called = []
        reader = _ChunkReader(b"")
        reader_ref = weakref.ref(reader)
        part.data_cb(0, reader, free=_free_append_called, userdata=called)

        if replacement_kind == "data":
            part.data(b"value")
        elif replacement_kind == "filedata":
            part.filedata(str(fixture_data_path))
        else:
            child = pycurl.Mime(curl)
            part.subparts(child)

        del reader
        gc.collect()
        assert reader_ref() is None

        mime.close()
        assert called == ["called"]


def test_mime_part_methods_fail_after_parent_close():
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        part = mime.addpart()

        mime.close()

        with pytest.raises(pycurl.error, match="no mime handle"):
            part.name("field")


def test_mime_subparts_transfers_ownership():
    with pycurl.Curl() as curl:
        parent = pycurl.Mime(curl)
        child = pycurl.Mime(curl)

        child_part = child.addpart()
        child_part.name("nested")
        child_part.data("value")

        parent_part = parent.addpart()
        parent_part.subparts(child)
        assert child.closed() is False

        child.addpart()
        parent.close()
        assert child.closed() is True

        with pytest.raises(pycurl.error, match="no mime handle"):
            child.addpart()


def test_mime_subparts_requires_same_curl_handle():
    with pycurl.Curl() as curl1, pycurl.Curl() as curl2:
        parent = pycurl.Mime(curl1)
        child = pycurl.Mime(curl2)

        part = parent.addpart()
        with pytest.raises(ValueError, match="same Curl handle"):
            part.subparts(child)


def test_mime_subparts_rejects_already_attached_mime():
    with pycurl.Curl() as curl:
        parent1 = pycurl.Mime(curl)
        parent2 = pycurl.Mime(curl)
        child = pycurl.Mime(curl)

        parent1.addpart().subparts(child)
        with pytest.raises(ValueError, match="already attached"):
            parent2.addpart().subparts(child)


def test_mime_subparts_rejects_mimepost_pinned_mime():
    with pycurl.Curl() as curl:
        parent = pycurl.Mime(curl)
        child = pycurl.Mime(curl)
        curl.setopt(pycurl.MIMEPOST, child)

        with pytest.raises(ValueError, match="currently set as MIMEPOST"):
            parent.addpart().subparts(child)


def test_mime_subparts_failure_rolls_back_parent_reference():
    with pycurl.Curl() as curl:
        parent = _make_tracking_mime(curl)
        child = pycurl.Mime(curl)

        parent.addpart().subparts(child)
        child_part = child.addpart()

        with pytest.raises(pycurl.error):
            child_part.subparts(parent)

        parent_ref = weakref.ref(parent)
        parent = None
        gc.collect()
        assert parent_ref() is None


@pytest.mark.parametrize("helper_name", ["add", "add_field"])
def test_mime_add_data_helpers_set_common_fields(helper_name, data_value):
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        part = _add_data_part(mime, helper_name, data_value)
        assert isinstance(part, pycurl.MimePart)


def test_mime_add_builder_rejects_data_and_file_together(fixture_data_path):
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        with pytest.raises(ValueError, match="at most one of data or file"):
            mime.add(name="field", data="value", file=str(fixture_data_path))


@pytest.mark.parametrize(
    "helper_name,bad_kwargs",
    [
        ("add", {"name": "bad", "data": "bad-value", "headers": object()}),
        ("add_field", {"name": "bad", "value": "bad-value", "headers": object()}),
    ],
)
def test_mime_add_data_helpers_validation_is_transactional(
    app, helper_name, bad_kwargs
):
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)

        with pytest.raises(TypeError, match="headers must be a list or tuple"):
            getattr(mime, helper_name)(**bad_kwargs)

        mime.add_field("good", "good-value")
        curl.setopt(pycurl.MIMEPOST, mime)

        assert _perform_json(curl, f"{app}/postfields") == {"good": "good-value"}


def test_mime_add_file_validation_is_transactional(app, tmp_path):
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        missing_path = tmp_path / "missing.bin"

        with pytest.raises(pycurl.error, match="Failed to open/read local data"):
            mime.add_file("bad", str(missing_path))

        mime.add_field("good", "good-value")
        curl.setopt(pycurl.MIMEPOST, mime)

        assert _perform_json(curl, f"{app}/postfields") == {"good": "good-value"}


def test_mime_add_file_helper(fixture_data_path):
    with pycurl.Curl() as curl:
        mime = pycurl.Mime(curl)
        part = mime.add_file(
            "upload",
            str(fixture_data_path),
            filename="upload.bin",
            content_type="application/octet-stream",
            headers=["X-Test: yes"],
            encoder="binary",
        )
        assert isinstance(part, pycurl.MimePart)


def test_mime_add_multipart_helper():
    with pycurl.Curl() as curl:
        parent = pycurl.Mime(curl)
        child = parent.add_multipart(name="nested")

        assert isinstance(child, pycurl.Mime)
        assert child.closed() is False

        child.add_field("inner", "value")
        parent.add_multipart(name="without-type", subtype=None)

        parent.close()
        assert child.closed() is True
