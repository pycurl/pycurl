import gc
import io
import json
import weakref

import pytest

import pycurl

from . import util


def _check_header_echo(handle, app, value, persists=True):
    body = io.BytesIO()
    handle.setopt(pycurl.WRITEFUNCTION, body.write)
    handle.setopt(pycurl.URL, f"{app}/header_utf8?h=x-test-header")
    handle.perform()
    assert (body.getvalue().decode("utf-8") == value) == persists


def _check_postfields_echo(handle, app, value, persists=True):
    body = io.BytesIO()
    handle.setopt(pycurl.WRITEFUNCTION, body.write)
    handle.setopt(pycurl.URL, f"{app}/postfields")
    handle.perform()
    assert (json.loads(body.getvalue()) == value) == persists


def test_duphandle_attribute_dict():
    orig = util.DefaultCurl()
    orig.orig_attr = "orig-value"
    # attribute dict should be copied - the *object*, not the reference
    dup = orig.duphandle()
    assert dup.orig_attr == "orig-value"
    # cloned dict should be a separate object
    dup.dup_attr = "dup-value"
    with pytest.raises(
        AttributeError, match="trying to obtain a non-existing attribute: dup_attr"
    ):
        _ = orig.dup_attr
    # dealloc orig - original dict is freed from memory
    orig.close()
    del orig
    # cloned dict should still exist
    assert dup.orig_attr == "orig-value"
    assert dup.dup_attr == "dup-value"
    dup.close()


@pytest.mark.parametrize(
    "clear",
    [
        # util_curl_xdecref()
        pytest.param(lambda c: c.reset(), id="reset"),
        # util_curl_unsetopt()
        pytest.param(lambda c: c.unsetopt(pycurl.HTTPHEADER), id="unsetopt"),
    ],
)
def test_duphandle_slist(curl, app, clear):
    # new slist object is created with ref count = 1
    curl.setopt(pycurl.HTTPHEADER, ["x-test-header: orig-slist"])
    # ref is copied and object incref'ed
    with curl.duphandle() as dup1:
        # slist object is decref'ed and ref set to null
        clear(curl)
        # null ref is copied - no effect
        with curl.duphandle() as dup2:
            # check slist object persistence
            _check_header_echo(dup1, app, "orig-slist", True)
            _check_header_echo(dup2, app, "orig-slist", False)
            # check overwriting - orig slist is decref'ed to 0 and finally
            # deallocated, util_curlslist_update() and util_curlslist_dealloc()
            dup1.setopt(pycurl.HTTPHEADER, ["x-test-header: dup-slist"])
            _check_header_echo(dup1, app, "dup-slist", True)


@pytest.mark.parametrize(
    "clear",
    [
        # util_curl_xdecref()
        pytest.param(lambda c: c.reset(), id="reset"),
        # util_curl_unsetopt()
        pytest.param(lambda c: c.unsetopt(pycurl.HTTPPOST), id="unsetopt"),
    ],
)
def test_duphandle_httppost(curl, app, clear):
    with pytest.warns(DeprecationWarning, match="HTTPPOST is deprecated; use MIMEPOST"):
        curl.setopt(
            pycurl.HTTPPOST,
            [("field", (pycurl.FORM_CONTENTS, "orig-httppost"))],
        )
    with curl.duphandle() as dup1:
        clear(curl)
        with curl.duphandle() as dup2:
            _check_postfields_echo(dup1, app, {"field": "orig-httppost"}, True)
            _check_postfields_echo(dup2, app, {"field": "orig-httppost"}, False)
            # util_curlhttppost_update() and util_curlhttppost_dealloc()
            with pytest.warns(
                DeprecationWarning, match="HTTPPOST is deprecated; use MIMEPOST"
            ):
                dup1.setopt(
                    pycurl.HTTPPOST,
                    [("field", (pycurl.FORM_CONTENTS, "dup-httppost"))],
                )
            _check_postfields_echo(dup1, app, {"field": "dup-httppost"}, True)


def test_duphandle_references(app):
    body = io.BytesIO()

    def callback(data):
        body.write(data)

    callback_ref = weakref.ref(callback)
    # preliminary checks of gc and weakref working as expected
    assert gc.get_referrers(callback) == []
    assert callback_ref() is not None
    orig = util.DefaultCurl()
    # setopt - callback ref is copied and callback incref'ed
    orig.setopt(pycurl.WRITEFUNCTION, callback)
    assert gc.get_referrers(callback) == [orig]
    # duphandle - callback ref is copied and callback incref'ed
    dup = orig.duphandle()
    assert set(gc.get_referrers(callback)) == {orig, dup}
    # dealloc orig and decref callback
    orig.close()
    del orig
    assert gc.get_referrers(callback) == [dup]
    # decref callback again - back to ref count = 1
    del callback
    assert callback_ref() is not None
    # check that callback object still exists and is invoked
    dup.setopt(pycurl.URL, f"{app}/success")
    dup.perform()
    assert body.getvalue().decode("utf-8") == "success"
    # final decref - callback is deallocated
    dup.close()
    assert callback_ref() is None


def test_duphandle_while_performing(curl, app):
    body = io.BytesIO()
    dups = []

    def write_cb(data):
        if not dups:
            dups.append(curl.duphandle())
        return body.write(data)

    curl.setopt(pycurl.WRITEFUNCTION, write_cb)
    curl.setopt(pycurl.URL, f"{app}/success")
    curl.perform()
    assert body.getvalue().decode("utf-8") == "success"
    with dups[0] as dup:
        dup_body = io.BytesIO()
        dup.setopt(pycurl.WRITEFUNCTION, dup_body.write)
        dup.perform()
        assert dup_body.getvalue().decode("utf-8") == "success"


def test_duphandle_after_close_raises(curl):
    curl.close()
    with pytest.raises(pycurl.error, match="no curl handle"):
        curl.duphandle()
