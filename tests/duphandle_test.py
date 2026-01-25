#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import gc
import weakref
import pytest

try:
    import json
except ImportError:
    import simplejson as json

from . import util


@pytest.fixture
def orig():
    curl = util.DefaultCurl()
    yield curl
    curl.close()


def slist_check(handle, base_url, value, persistance=True):
    body = util.BytesIO()
    handle.setopt(pycurl.WRITEFUNCTION, body.write)
    handle.setopt(pycurl.URL, f"{base_url}/header_utf8?h=x-test-header")
    handle.perform()
    result = body.getvalue().decode("utf-8")
    assert (result == value) == persistance


def slist_test(orig, base_url, clear_func, *args):
    # new slist object is created with ref count = 1
    orig.setopt(pycurl.HTTPHEADER, ["x-test-header: orig-slist"])
    # ref is copied and object incref'ed
    dup1 = orig.duphandle()
    # slist object is decref'ed and ref set to null
    clear_func(*args)
    # null ref is copied - no effect
    dup2 = orig.duphandle()
    # check slist object persistance
    slist_check(dup1, base_url, "orig-slist", True)
    slist_check(dup2, base_url, "orig-slist", False)
    # check overwriting - orig slist is decref'ed to 0 and finally deallocated
    # util_curlslist_update() and util_curlslist_dealloc()
    dup1.setopt(pycurl.HTTPHEADER, ["x-test-header: dup-slist"])
    slist_check(dup1, base_url, "dup-slist", True)
    # cleanup
    dup1.close()
    dup2.close()
    orig.close()


def httppost_check(handle, base_url, value, persistance=True):
    body = util.BytesIO()
    handle.setopt(pycurl.WRITEFUNCTION, body.write)
    handle.setopt(pycurl.URL, f"{base_url}/postfields")
    handle.perform()
    result = json.loads(body.getvalue())
    assert (result == value) == persistance


def post_test(orig, base_url, clear_func, *args, opt=pycurl.HTTPPOST):
    orig.setopt(
        opt,
        [
            ("field", (pycurl.FORM_CONTENTS, "orig-httppost")),
        ],
    )
    dup1 = orig.duphandle()
    clear_func(*args)
    dup2 = orig.duphandle()
    httppost_check(dup1, base_url, {"field": "orig-httppost"}, True)
    httppost_check(dup2, base_url, {"field": "orig-httppost"}, False)
    # util_curlpost_update() and util_curlhttppost_dealloc()
    dup1.setopt(
        opt,
        [
            ("field", (pycurl.FORM_CONTENTS, "dup-httppost")),
        ],
    )
    httppost_check(dup1, base_url, {"field": "dup-httppost"}, True)
    dup1.close()
    dup2.close()
    orig.close()


def test_attribute_dict(orig):
    orig.orig_attr = "orig-value"
    # attribute dict should be copied - the *object*, not the reference
    dup = orig.duphandle()
    assert dup.orig_attr == "orig-value"
    # cloned dict should be a separate object
    dup.dup_attr = "dup-value"
    try:
        orig.dup_attr == "does not exist"
    except AttributeError as error:
        assert "trying to obtain a non-existing attribute: dup_attr" in str(error.args)
    else:
        raise AssertionError("should have raised AttributeError")
    # dealloc orig - original dict is freed from memory
    orig.close()
    del orig
    # cloned dict should still exist
    assert dup.orig_attr == "orig-value"
    assert dup.dup_attr == "dup-value"
    dup.close()


def test_slist_xdecref(app, orig):
    # util_curl_xdecref()
    slist_test(orig, app, orig.reset)


def test_slist_unsetopt(app, orig):
    # util_curl_unsetopt()
    slist_test(orig, app, orig.unsetopt, pycurl.HTTPHEADER)


def test_post_xdecref(app, post_opt, orig):
    # util_curl_xdecref()
    post_test(orig, app, orig.reset, opt=post_opt)


def test_post_unsetopt(app, post_opt, orig):
    # util_curl_unsetopt()
    post_test(orig, app, orig.unsetopt, post_opt, opt=post_opt)


def test_post_independent_after_orig_change(app, post_opt, orig):
    orig.setopt(
        post_opt,
        [
            ("field", (pycurl.FORM_CONTENTS, "orig-post")),
        ],
    )
    dup = orig.duphandle()
    orig.setopt(
        post_opt,
        [
            ("field", (pycurl.FORM_CONTENTS, "updated-post")),
        ],
    )
    httppost_check(orig, app, {"field": "updated-post"}, True)
    httppost_check(dup, app, {"field": "orig-post"}, True)
    dup.close()
    orig.close()


def test_post_after_orig_close(app, post_opt, orig):
    orig.setopt(
        post_opt,
        [
            ("field", (pycurl.FORM_CONTENTS, "orig-post")),
        ],
    )
    dup = orig.duphandle()
    orig.close()
    del orig
    httppost_check(dup, app, {"field": "orig-post"}, True)
    dup.close()


def test_references(app, orig):
    body = util.BytesIO()

    def callback(data):
        body.write(data)

    callback_ref = weakref.ref(callback)
    # preliminary checks of gc and weakref working as expected
    assert gc.get_referrers(callback) == []
    assert callback_ref() is not None
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
    result = body.getvalue().decode("utf-8")
    assert result == "success"
    # final decref - callback is deallocated
    dup.close()
    assert callback_ref() is None
