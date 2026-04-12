#! /usr/bin/env python
# vi:ts=4:et

import pycurl
import unittest
import gc
import flaky
import weakref

from . import util

debug = False


@flaky.flaky(max_runs=3)
class MultiMemoryMgmtTest(unittest.TestCase):
    def test_opensocketfunction_collection(self):
        self.check_callback(pycurl.M_SOCKETFUNCTION)

    def test_seekfunction_collection(self):
        self.check_callback(pycurl.M_TIMERFUNCTION)

    def check_callback(self, callback):
        # Note: extracting a context manager seems to result in
        # everything being garbage collected even if the C code
        # does not clear the callback
        object_count = 0
        gc.collect()
        # gc.collect() can create new objects... running it again here
        # settles tracked object count for the actual test below
        gc.collect()
        object_count = len(gc.get_objects())

        c = pycurl.CurlMulti()
        c.setopt(callback, lambda x: True)
        del c

        gc.collect()
        new_object_count = len(gc.get_objects())
        # it seems that GC sometimes collects something that existed
        # before this test ran, GH issues #273/#274
        self.assertIn(new_object_count, (object_count, object_count - 1))

    def test_socketfunction_reassignment(self):
        self.check_callback_reassignment(pycurl.M_SOCKETFUNCTION)

    def test_timerfunction_reassignment(self):
        self.check_callback_reassignment(pycurl.M_TIMERFUNCTION)

    def check_callback_reassignment(self, callback):
        """Setting a multi callback twice must not leak the old callback."""
        import sys

        def first_cb(x):
            return True

        m = pycurl.CurlMulti()
        m.setopt(callback, first_cb)
        refcount_before = sys.getrefcount(first_cb)

        def second_cb(x):
            return False

        m.setopt(callback, second_cb)
        refcount_after = sys.getrefcount(first_cb)

        # After reassignment the old callback should have been released,
        # so its refcount should have dropped by 1.
        self.assertEqual(refcount_after, refcount_before - 1)

        del m
        gc.collect()

    def test_curl_ref(self):
        c = util.DefaultCurl()
        m = pycurl.CurlMulti()

        ref = weakref.ref(c)
        m.add_handle(c)
        del c

        assert ref()
        gc.collect()
        assert ref()

        m.remove_handle(ref())
        gc.collect()
        assert ref() is None
