#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import gc
import pycurl
import pytest
import unittest
import select

from . import appmanager
from . import util

setup_module_1, teardown_module_1 = appmanager.setup(("app", 8380))
setup_module_2, teardown_module_2 = appmanager.setup(("app", 8381))
setup_module_3, teardown_module_3 = appmanager.setup(("app", 8382))


def setup_module(mod):
    setup_module_1(mod)
    setup_module_2(mod)
    setup_module_3(mod)


def teardown_module(mod):
    teardown_module_3(mod)
    teardown_module_2(mod)
    teardown_module_1(mod)


class MultiTest(unittest.TestCase):
    def test_multi(self):
        io1 = util.BytesIO()
        io2 = util.BytesIO()
        m = pycurl.CurlMulti()
        handles = []
        c1 = util.DefaultCurl()
        c2 = util.DefaultCurl()
        c1.setopt(c1.URL, "http://%s:8380/success" % localhost)
        c1.setopt(c1.WRITEFUNCTION, io1.write)
        c2.setopt(c2.URL, "http://%s:8381/success" % localhost)
        c2.setopt(c1.WRITEFUNCTION, io2.write)
        m.add_handle(c1)
        m.add_handle(c2)
        handles.append(c1)
        handles.append(c2)

        num_handles = len(handles)
        while num_handles:
            _, num_handles = m.perform()
            m.select(1.0)

        m.remove_handle(c2)
        m.remove_handle(c1)
        m.close()
        c1.close()
        c2.close()

        self.assertEqual("success", io1.getvalue().decode())
        self.assertEqual("success", io2.getvalue().decode())

    def test_multi_select_fdset(self):
        c1 = util.DefaultCurl()
        c2 = util.DefaultCurl()
        c3 = util.DefaultCurl()
        c1.setopt(c1.URL, "http://%s:8380/success" % localhost)
        c2.setopt(c2.URL, "http://%s:8381/success" % localhost)
        c3.setopt(c3.URL, "http://%s:8382/success" % localhost)
        c1.body = util.BytesIO()
        c2.body = util.BytesIO()
        c3.body = util.BytesIO()
        c1.setopt(c1.WRITEFUNCTION, c1.body.write)
        c2.setopt(c2.WRITEFUNCTION, c2.body.write)
        c3.setopt(c3.WRITEFUNCTION, c3.body.write)

        m = pycurl.CurlMulti()
        m.add_handle(c1)
        m.add_handle(c2)
        m.add_handle(c3)

        # Number of seconds to wait for a timeout to happen
        SELECT_TIMEOUT = 0.1

        # Stir the state machine into action
        _, num_handles = m.perform()

        # Keep going until all the connections have terminated
        while num_handles:
            select.select(*m.fdset() + (SELECT_TIMEOUT,))
            _, num_handles = m.perform()

        # Cleanup
        for handle in (c1, c2, c3):
            assert handle.multi() == m
            handle.multi().remove_handle(handle)
            assert handle.multi() is None
        m.close()
        c1.close()
        c2.close()
        c3.close()

        self.assertEqual("success", c1.body.getvalue().decode())
        self.assertEqual("success", c2.body.getvalue().decode())
        self.assertEqual("success", c3.body.getvalue().decode())

    def test_multi_status_codes(self):
        # init
        m = pycurl.CurlMulti()
        m.handles = []
        urls = [
            "http://%s:8380/success" % localhost,
            "http://%s:8381/status/403" % localhost,
            "http://%s:8382/status/404" % localhost,
        ]
        for url in urls:
            c = util.DefaultCurl()
            # save info in standard Python attributes
            c.url = url.rstrip()
            c.body = util.BytesIO()
            c.http_code = -1
            m.handles.append(c)
            # pycurl API calls
            c.setopt(c.URL, c.url)
            c.setopt(c.WRITEFUNCTION, c.body.write)
            m.add_handle(c)

        # get data
        num_handles = len(m.handles)
        while num_handles:
            _, num_handles = m.perform()
            # currently no more I/O is pending, could do something in the meantime
            # (display a progress bar, etc.)
            m.select(0.1)

        # close handles
        for c in m.handles:
            # save info in standard Python attributes
            c.http_code = c.getinfo(c.HTTP_CODE)
            # pycurl API calls
            m.remove_handle(c)
            c.close()
        m.close()

        # check result
        self.assertEqual("success", m.handles[0].body.getvalue().decode())
        self.assertEqual(200, m.handles[0].http_code)
        # bottle generated response body
        self.assertEqual("forbidden", m.handles[1].body.getvalue().decode())
        self.assertEqual(403, m.handles[1].http_code)
        # bottle generated response body
        self.assertEqual("not found", m.handles[2].body.getvalue().decode())
        self.assertEqual(404, m.handles[2].http_code)

    def check_adding_closed_handle(self, close_fn):
        # init
        m = pycurl.CurlMulti()
        m.handles = []
        urls = [
            "http://%s:8380/success" % localhost,
            "http://%s:8381/status/403" % localhost,
            "http://%s:8382/status/404" % localhost,
        ]
        for url in urls:
            c = util.DefaultCurl()
            # save info in standard Python attributes
            c.url = url
            c.body = util.BytesIO()
            c.http_code = -1
            c.debug = 0
            m.handles.append(c)
            # pycurl API calls
            c.setopt(c.URL, c.url)
            c.setopt(c.WRITEFUNCTION, c.body.write)
            m.add_handle(c)

        # debug - close a handle
        c = m.handles[2]
        c.debug = 1
        c.close()

        # get data
        num_handles = len(m.handles)
        while num_handles:
            _, num_handles = m.perform()
            # currently no more I/O is pending, could do something in the meantime
            # (display a progress bar, etc.)
            m.select(0.1)

        # close handles
        for c in m.handles:
            # save info in standard Python attributes
            try:
                c.http_code = c.getinfo(c.HTTP_CODE)
            except pycurl.error:
                # handle already closed - see debug above
                assert c.debug
                c.http_code = -1
            # pycurl API calls
            close_fn(m, c)
        m.close()

        # check result
        self.assertEqual("success", m.handles[0].body.getvalue().decode())
        self.assertEqual(200, m.handles[0].http_code)
        # bottle generated response body
        self.assertEqual("forbidden", m.handles[1].body.getvalue().decode())
        self.assertEqual(403, m.handles[1].http_code)
        # bottle generated response body
        self.assertEqual("", m.handles[2].body.getvalue().decode())
        self.assertEqual(-1, m.handles[2].http_code)

    def _remove_then_close(self, m, c):
        m.remove_handle(c)
        c.close()

    def _close_then_remove(self, m, c):
        # in the C API this is the wrong calling order, but pycurl
        # handles this automatically
        c.close()
        m.remove_handle(c)

    def _close_without_removing(self, m, c):
        # actually, remove_handle is called automatically on close
        c.close()

    def test_adding_closed_handle_remove_then_close(self):
        self.check_adding_closed_handle(self._remove_then_close)

    def test_adding_closed_handle_close_then_remove(self):
        self.check_adding_closed_handle(self._close_then_remove)

    def test_adding_closed_handle_close_without_removing(self):
        self.check_adding_closed_handle(self._close_without_removing)

    def test_multi_select(self):
        c1 = util.DefaultCurl()
        c2 = util.DefaultCurl()
        c3 = util.DefaultCurl()
        c1.setopt(c1.URL, "http://%s:8380/success" % localhost)
        c2.setopt(c2.URL, "http://%s:8381/success" % localhost)
        c3.setopt(c3.URL, "http://%s:8382/success" % localhost)
        c1.body = util.BytesIO()
        c2.body = util.BytesIO()
        c3.body = util.BytesIO()
        c1.setopt(c1.WRITEFUNCTION, c1.body.write)
        c2.setopt(c2.WRITEFUNCTION, c2.body.write)
        c3.setopt(c3.WRITEFUNCTION, c3.body.write)

        m = pycurl.CurlMulti()
        m.add_handle(c1)
        m.add_handle(c2)
        m.add_handle(c3)

        # Number of seconds to wait for a timeout to happen
        SELECT_TIMEOUT = 1.0

        # Stir the state machine into action
        _, num_handles = m.perform()

        # Keep going until all the connections have terminated
        while num_handles:
            # The select method uses fdset internally to determine which file descriptors
            # to check.
            m.select(SELECT_TIMEOUT)
            _, num_handles = m.perform()

        # Cleanup
        m.remove_handle(c3)
        m.remove_handle(c2)
        m.remove_handle(c1)
        m.close()
        c1.close()
        c2.close()
        c3.close()

        self.assertEqual("success", c1.body.getvalue().decode())
        self.assertEqual("success", c2.body.getvalue().decode())
        self.assertEqual("success", c3.body.getvalue().decode())

    def test_multi_info_read(self):
        c1 = util.DefaultCurl()
        c2 = util.DefaultCurl()
        c3 = util.DefaultCurl()
        c1.setopt(c1.URL, "http://%s:8380/short_wait" % localhost)
        c2.setopt(c2.URL, "http://%s:8381/short_wait" % localhost)
        c3.setopt(c3.URL, "http://%s:8382/short_wait" % localhost)
        c1.body = util.BytesIO()
        c2.body = util.BytesIO()
        c3.body = util.BytesIO()
        c1.setopt(c1.WRITEFUNCTION, c1.body.write)
        c2.setopt(c2.WRITEFUNCTION, c2.body.write)
        c3.setopt(c3.WRITEFUNCTION, c3.body.write)

        m = pycurl.CurlMulti()
        m.add_handle(c1)
        m.add_handle(c2)
        m.add_handle(c3)

        # Number of seconds to wait for a timeout to happen
        SELECT_TIMEOUT = 1.0

        # Stir the state machine into action
        _, num_handles = m.perform()

        infos = []
        # Keep going until all the connections have terminated
        while num_handles:
            # The select method uses fdset internally to determine which file descriptors
            # to check.
            m.select(SELECT_TIMEOUT)
            _, num_handles = m.perform()
            info = m.info_read()
            infos.append(info)

        all_handles = []
        for info in infos:
            handles = info[1]
            # last info is an empty array
            if handles:
                all_handles.extend(handles)

        self.assertEqual(3, len(all_handles))
        assert c1 in all_handles
        assert c2 in all_handles
        assert c3 in all_handles

        # Cleanup
        m.remove_handle(c3)
        m.remove_handle(c2)
        m.remove_handle(c1)
        m.close()
        c1.close()
        c2.close()
        c3.close()

        self.assertEqual("success", c1.body.getvalue().decode())
        self.assertEqual("success", c2.body.getvalue().decode())
        self.assertEqual("success", c3.body.getvalue().decode())

    def test_multi_info_read_some(self):
        """
        Check for missing messages from info_read when restricted to less than all messages

        This is a regression check for an issue where the (n+1)'th queued message went
        missing when (n < number of messages in the queue) and info_read(num_messages=n) was
        called.
        """
        c1 = util.DefaultCurl()
        c2 = util.DefaultCurl()
        c3 = util.DefaultCurl()
        c1.setopt(c1.URL, "http://%s:8380/short_wait" % localhost)
        c2.setopt(c2.URL, "http://%s:8381/short_wait" % localhost)
        c3.setopt(c3.URL, "http://%s:8382/short_wait" % localhost)
        c1.body = util.BytesIO()
        c2.body = util.BytesIO()
        c3.body = util.BytesIO()
        c1.setopt(c1.WRITEFUNCTION, c1.body.write)
        c2.setopt(c2.WRITEFUNCTION, c2.body.write)
        c3.setopt(c3.WRITEFUNCTION, c3.body.write)

        m = pycurl.CurlMulti()
        m.add_handle(c1)
        m.add_handle(c2)
        m.add_handle(c3)

        # Complete all requests
        num_handles = -1
        while num_handles:
            _, num_handles = m.perform()
            m.select(1.0)

        # Three messages in the queue, read two
        remaining, success, error = m.info_read(2)
        assert remaining == 1
        assert len(success) + len(error) == 2

        # One message left in the queue
        remaining, success, error = m.info_read()
        assert remaining == 0
        assert len(success) + len(error) == 1

    def test_multi_constructor(self):
        pycurl.CurlMulti()
        pycurl.CurlMulti(close_handles=True)

    def test_multi_close(self):
        m = pycurl.CurlMulti()
        assert not m.closed()
        m.close()
        assert m.closed()

    def test_multi_close_twice(self):
        m = pycurl.CurlMulti()
        assert not m.closed()
        m.close()
        assert m.closed()
        m.close()
        assert m.closed()

        m = pycurl.CurlMulti(close_handles=True)
        assert not m.closed()
        m.close()
        assert m.closed()
        m.close()
        assert m.closed()

    def test_close_handles_false(self):
        easy1 = pycurl.Curl()
        easy2 = pycurl.Curl()
        assert easy1.multi() is None
        assert easy2.multi() is None
        m = pycurl.CurlMulti()
        m.add_handle(easy1)
        m.add_handle(easy2)
        assert m == easy1.multi()
        assert m == easy2.multi()
        m.close()
        assert m.closed()
        assert not easy1.closed()
        assert not easy2.closed()
        assert easy1.multi() is None
        assert easy2.multi() is None

    def test_close_handles_true(self):
        easy1 = pycurl.Curl()
        easy2 = pycurl.Curl()
        assert easy1.multi() is None
        assert easy2.multi() is None
        m = pycurl.CurlMulti(close_handles=True)
        m.add_handle(easy1)
        m.add_handle(easy2)
        assert m == easy1.multi()
        assert m == easy2.multi()
        m.close()
        assert easy1.closed()
        assert easy2.closed()
        assert easy1.closed()
        assert easy2.closed()
        assert easy1.multi() is None
        assert easy2.multi() is None

    # positional arguments are rejected
    def test_positional_arguments(self):
        with pytest.raises(TypeError):
            pycurl.CurlMulti(1)

    # keyword arguments are rejected
    def test_keyword_arguments(self):
        with pytest.raises(TypeError):
            pycurl.CurlMulti(a=1)

    def test_context_manager_close_no_handles_false(self):
        with pycurl.CurlMulti() as _:
            pass

    def test_context_manager_close_no_handles_true(self):
        with pycurl.CurlMulti(close_handles=True) as _:
            pass

    def test_context_manager_close_handles_false(self):
        easy1 = pycurl.Curl()
        easy2 = pycurl.Curl()

        with pycurl.CurlMulti() as m:
            m.add_handle(easy1)
            m.add_handle(easy2)
            assert m == easy1.multi()
            assert m == easy2.multi()

        assert not easy1.closed()
        assert not easy2.closed()
        assert easy1.multi() is None
        assert easy2.multi() is None

        easy1.setopt(pycurl.URL, "https://example.com/")
        easy2.setopt(pycurl.URL, "https://example.com/")

        easy1.close()
        easy2.close()
        assert easy1.multi() is None
        assert easy2.multi() is None

    def test_context_manager_close_handles_true(self):
        easy1 = pycurl.Curl()
        easy2 = pycurl.Curl()

        with pycurl.CurlMulti(close_handles=True) as m:
            m.add_handle(easy1)
            m.add_handle(easy2)
            assert m == easy1.multi()
            assert m == easy2.multi()

        assert easy1.closed()
        assert easy2.closed()
        assert easy1.multi() is None
        assert easy2.multi() is None

        with pytest.raises(Exception):
            easy1.setopt(pycurl.URL, "https://example.com/")
        with pytest.raises(Exception):
            easy2.setopt(pycurl.URL, "https://example.com/")

    def test_multi_garbage_collection(self):
        easy1 = pycurl.Curl()
        easy2 = pycurl.Curl()
        assert easy1.multi() is None
        assert easy2.multi() is None
        m = pycurl.CurlMulti()
        m.add_handle(easy1)
        m.add_handle(easy2)
        assert m == easy1.multi()
        assert m == easy2.multi()

        del m
        gc.collect()

        assert easy1.multi() is None
        assert easy2.multi() is None

    def test_contains(self):
        class CurlLike(pycurl.Curl):
            pass

        m = pycurl.CurlMulti()
        easy1 = pycurl.Curl()
        easy1.bar = "bar"
        easy2 = CurlLike()
        easy2.foo = "foo"

        with pytest.raises(TypeError):
            123 in m
        with pytest.raises(TypeError):
            "not a curl" in m
        with pytest.raises(TypeError):
            None in m

        assert easy1 not in m
        assert easy2 not in m

        m.add_handle(easy1)
        assert easy1 in m
        assert easy2 not in m

        m.add_handle(easy2)
        assert easy1 in m
        assert easy2 in m

        m.remove_handle(easy1)
        assert easy1 not in m
        assert easy2 in m

        m.close()
        assert m.closed()
        assert easy2 not in m
