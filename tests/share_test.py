#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import threading
import pycurl
import pytest

from . import util


def set_share_defaults(s: pycurl.CurlShare):
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_COOKIE)
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_DNS)
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_SSL_SESSION)


@pytest.fixture
def default_share() -> pycurl.CurlShare:
    s = pycurl.CurlShare()
    set_share_defaults(s)
    return s


@pytest.fixture
def default_share_no_detach() -> pycurl.CurlShare:
    s = pycurl.CurlShare(detach_on_close=False)
    set_share_defaults(s)
    return s


class WorkerThread(threading.Thread):
    def __init__(self, share: pycurl.CurlShare, url: str):
        threading.Thread.__init__(self)
        self.curl = util.DefaultCurl()
        self.curl.setopt(pycurl.URL, url + "/success")
        self.curl.setopt(pycurl.SHARE, share)
        self.sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, self.sio.write)

    def run(self):
        self.curl.perform()
        self.curl.close()


def test_share(app, default_share):
    s = default_share

    t1 = WorkerThread(s, url=app)
    t2 = WorkerThread(s, url=app)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    del s

    assert t1.sio.getvalue().decode() == "success"
    assert t2.sio.getvalue().decode() == "success"


def test_share_close():
    s = pycurl.CurlShare()
    assert not s.closed()
    s.close()
    assert s.closed()


def test_share_close_twice():
    s = pycurl.CurlShare()
    assert not s.closed()
    s.close()
    assert s.closed()
    s.close()
    assert s.closed()


# positional arguments are rejected
def test_positional_arguments():
    with pytest.raises(TypeError):
        pycurl.CurlShare(1)


# keyword arguments are rejected
def test_keyword_arguments():
    with pytest.raises(TypeError):
        pycurl.CurlShare(a=1)


def test_detach_on_close_keyword_argument_accepted():
    s1 = pycurl.CurlShare(detach_on_close=True)
    s2 = pycurl.CurlShare(detach_on_close=False)
    assert not s1.closed()
    assert not s2.closed()
    s1.close()
    s2.close()
    assert s1.closed()
    assert s2.closed()


def test_easy_with_share_closed_before_perform(app, default_share):
    s = default_share
    n_easies = 10
    easies = []
    for _ in range(n_easies):
        c = util.DefaultCurl()
        c.setopt(pycurl.URL, app + "/success")
        c.setopt(pycurl.SHARE, s)

        sio = util.BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, sio.write)

        easies.append((c, sio))

    s.close()
    assert s.closed()

    for c, _ in easies:
        assert c.share() is None
        assert not c.closed()


def test_easy_with_share_closed_before_perform_no_detach(app, default_share_no_detach):
    s = default_share_no_detach
    n_easies = 10
    easies = []
    for _ in range(n_easies):
        c = util.DefaultCurl()
        c.setopt(pycurl.URL, app + "/success")
        c.setopt(pycurl.SHARE, s)

        sio = util.BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, sio.write)

        easies.append((c, sio))

    with pytest.raises(pycurl.error):
        s.close()
    assert not s.closed()

    for c, _ in easies:
        assert c.share() == s

    for c, sio in easies:
        for _ in range(3):
            sio.seek(0)
            sio.truncate(0)
            c.perform()
            assert sio.getvalue().decode() == "success"

    n = len(easies)
    q1 = n // 4
    q3 = (3 * n) // 4

    for c, _ in easies[q1:q3]:
        c.unsetopt(pycurl.SHARE)

    for c, _ in easies[:q1] + easies[q3:]:
        c.close()
        assert c.closed()

    s.close()
    assert s.closed()


def test_easy_set_share_closed_raises(app):
    s = pycurl.CurlShare()
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_COOKIE)
    s.close()
    assert s.closed()

    c = util.DefaultCurl()
    c.setopt(pycurl.URL, app + "/success")

    with pytest.raises(RuntimeError) as excinfo:
        c.setopt(pycurl.SHARE, s)

    assert "CurlShare is closed" == str(excinfo.value)


def test_share_context_manager_detaches_by_default(app):
    c = util.DefaultCurl()
    c.setopt(pycurl.URL, app + "/success")
    sio = util.BytesIO()
    c.setopt(pycurl.WRITEFUNCTION, sio.write)

    with pycurl.CurlShare() as s:
        set_share_defaults(s)
        c.setopt(pycurl.SHARE, s)
        assert c.share() == s

    assert s.closed()
    assert c.share() is None

    sio.seek(0)
    sio.truncate(0)
    c.perform()
    assert sio.getvalue().decode() == "success"
    c.close()


def test_share_context_manager_strict_raises_if_live_easies(app):
    c = util.DefaultCurl()
    c.setopt(pycurl.URL, app + "/success")
    sio = util.BytesIO()
    c.setopt(pycurl.WRITEFUNCTION, sio.write)

    with pytest.raises(pycurl.error):
        with pycurl.CurlShare(detach_on_close=False) as s:
            set_share_defaults(s)
            c.setopt(pycurl.SHARE, s)
            assert c.share() == s

    assert not s.closed()
    assert c.share() == s

    c.unsetopt(pycurl.SHARE)
    s.close()
    c.close()
