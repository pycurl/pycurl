#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import os.path
import pycurl
import pytest

try:
    import json
except ImportError:
    import simplejson as json
try:
    import urllib.parse as urllib_parse
except ImportError:
    import urllib as urllib_parse

from . import util


@pytest.fixture
def curl():
    curl = util.DefaultCurl()
    yield curl
    curl.close()


def build_buffer_send(contents, variant):
    tuple_item = (
        "field2",
        (pycurl.FORM_BUFFER, "uploaded.file", pycurl.FORM_BUFFERPTR, contents),
    )
    list_item = [
        "field2",
        (pycurl.FORM_BUFFER, "uploaded.file", pycurl.FORM_BUFFERPTR, contents),
    ]
    list_item_inner = [
        "field2",
        [pycurl.FORM_BUFFER, "uploaded.file", pycurl.FORM_BUFFERPTR, contents],
    ]
    tuple_item_inner = (
        "field2",
        [pycurl.FORM_BUFFER, "uploaded.file", pycurl.FORM_BUFFERPTR, contents],
    )
    if variant == "list_tuple":
        return [tuple_item]
    if variant == "tuple_tuple":
        return (tuple_item,)
    if variant == "tuple_list":
        return (list_item,)
    if variant == "tuple_list_inner":
        return (tuple_item_inner,)
    if variant == "list_list":
        return [list_item_inner]
    raise AssertionError(f"unknown buffer variant: {variant}")


def urlencode_and_check(curl, base_url, pf):
    curl.setopt(pycurl.URL, f"{base_url}/postfields")
    postfields = urllib_parse.urlencode(pf)
    curl.setopt(pycurl.POSTFIELDS, postfields)
    sio = util.BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    curl.perform()
    assert curl.getinfo(pycurl.HTTP_CODE) == 200
    body = sio.getvalue().decode()
    returned_fields = json.loads(body)
    assert pf == returned_fields


def check_post(curl, send, expect, endpoint, post_opt):
    curl.setopt(pycurl.URL, endpoint)
    curl.setopt(post_opt, send)
    sio = util.BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    curl.perform()
    assert curl.getinfo(pycurl.HTTP_CODE) == 200
    body = sio.getvalue().decode()
    returned_fields = json.loads(body)
    assert expect == returned_fields


@pytest.mark.parametrize(
    "postfields",
    [
        pytest.param({"field1": "value1"}, id="single_field"),
        pytest.param(
            {"field1": "value1", "field2": "value2 with blanks", "field3": "value3"},
            id="multiple_fields",
        ),
        pytest.param(
            {
                "field1": "value1",
                "field2": "value2 with blanks and & chars",
                "field3": "value3",
            },
            id="fields_with_ampersand",
        ),
        pytest.param({"field1": ""}, id="empty_field_value"),
    ],
)
def test_urlencoded_fields(app, curl, postfields):
    urlencode_and_check(curl, app, postfields)


def test_with_null_byte(app, curl, post_opt):
    send = [
        ("field3", (pycurl.FORM_CONTENTS, "this is wei\000rd, but null-bytes are okay"))
    ]
    expect = {
        "field3": "this is wei\000rd, but null-bytes are okay",
    }
    check_post(curl, send, expect, f"{app}/postfields", post_opt)


def test_unsetopt_post_clears_form(app, curl, post_opt):
    curl.setopt(
        post_opt,
        [
            ("field1", (pycurl.FORM_CONTENTS, "value1")),
        ],
    )
    curl.unsetopt(post_opt)
    curl.setopt(pycurl.URL, f"{app}/postfields")
    sio = util.BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    curl.perform()
    assert curl.getinfo(pycurl.HTTP_CODE) == 200
    body = sio.getvalue().decode()
    returned_fields = json.loads(body)
    assert returned_fields == {}


@pytest.mark.skipif(
    util.pycurl_version_less_than(7, 56, 0),
    reason="MIMEPOST not supported by this libcurl version",
)
@pytest.mark.parametrize(
    "set_opt,unset_opt",
    [
        pytest.param(pycurl.MIMEPOST, pycurl.HTTPPOST, id="mimepost_then_unset_http"),
        pytest.param(pycurl.HTTPPOST, pycurl.MIMEPOST, id="httppost_then_unset_mime"),
    ],
)
def test_unsetopt_http_after_mimepost(app, curl, set_opt, unset_opt):
    curl.setopt(
        set_opt,
        [
            ("field1", (pycurl.FORM_CONTENTS, "value1")),
        ],
    )
    curl.unsetopt(unset_opt)
    curl.setopt(pycurl.URL, f"{app}/postfields")
    sio = util.BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, sio.write)
    curl.perform()
    assert curl.getinfo(pycurl.HTTP_CODE) == 200
    body = sio.getvalue().decode()
    returned_fields = json.loads(body)
    assert returned_fields == {}


def test_empty_file_content(app, curl, post_opt, tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text("")
    send = [
        ("field2", (pycurl.FORM_FILE, str(path))),
    ]
    expect = [
        {
            "name": "field2",
            "filename": path.name,
            "data": "",
        }
    ]
    check_post(curl, send, expect, f"{app}/files", post_opt)


def test_file(app, curl, post_opt):
    path = os.path.join(os.path.dirname(__file__), "..", "README.rst")
    f = open(path, newline="")
    try:
        contents = f.read()
    finally:
        f.close()
    send = [
        # ("field2", (pycurl.FORM_FILE, "test_post.py", pycurl.FORM_FILE, "test_post2.py")),
        ("field2", (pycurl.FORM_FILE, path)),
    ]
    expect = [
        {
            "name": "field2",
            "filename": "README.rst",
            "data": contents,
        }
    ]
    check_post(curl, send, expect, f"{app}/files", post_opt)


def test_form_and_file(app, curl, post_opt, tmp_path):
    path = tmp_path / "upload.txt"
    path.write_text("file-data")
    send = [
        ("field1", (pycurl.FORM_CONTENTS, "value1")),
        ("upload", (pycurl.FORM_FILE, str(path))),
    ]
    expect = {
        "form": {
            "field1": "value1",
        },
        "files": [
            {
                "name": "upload",
                "filename": path.name,
                "data": "file-data",
            }
        ],
    }
    check_post(curl, send, expect, f"{app}/form_and_files", post_opt)


def test_multiple_files(app, curl, post_opt, tmp_path):
    path_one = tmp_path / "file-one.txt"
    path_two = tmp_path / "file-two.txt"
    path_one.write_text("file-one")
    path_two.write_text("file-two")
    send = [
        ("file1", (pycurl.FORM_FILE, str(path_one))),
        ("file2", (pycurl.FORM_FILE, str(path_two))),
    ]
    expect = [
        {
            "name": "file1",
            "filename": path_one.name,
            "data": "file-one",
        },
        {
            "name": "file2",
            "filename": path_two.name,
            "data": "file-two",
        },
    ]
    check_post(curl, send, expect, f"{app}/files", post_opt)


@pytest.mark.parametrize(
    "contents,variant",
    [
        pytest.param(util.b("hello, world!"), "list_tuple", id="byte_list_tuple"),
        pytest.param(util.u("hello, world!"), "list_tuple", id="unicode_list_tuple"),
        pytest.param(util.u("hello, world!"), "tuple_tuple", id="tuple_tuple"),
        pytest.param(util.u("hello, world!"), "tuple_list", id="tuple_list"),
        pytest.param(
            util.u("hello, world!"), "tuple_list_inner", id="tuple_list_inner"
        ),
        pytest.param(util.u("hello, world!"), "list_list", id="list_list"),
    ],
)
def test_buffer_variants(app, curl, post_opt, contents, variant):
    send = build_buffer_send(contents, variant)
    expect = [
        {
            "name": "field2",
            "filename": "uploaded.file",
            "data": "hello, world!",
        }
    ]
    check_post(curl, send, expect, f"{app}/files", post_opt)
