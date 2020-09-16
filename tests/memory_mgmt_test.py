#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import sys
import weakref
import pycurl
import unittest
import gc
import flaky
from . import util

debug = False

if sys.platform == 'win32':
    devnull = 'NUL'
else:
    devnull = '/dev/null'

@flaky.flaky(max_runs=3)
class MemoryMgmtTest(unittest.TestCase):
    def maybe_enable_debug(self):
        if debug:
            flags = gc.DEBUG_COLLECTABLE | gc.DEBUG_UNCOLLECTABLE
            # python 3 has no DEBUG_OBJECTS
            if hasattr(gc, 'DEBUG_OBJECTS'):
                flags |= gc.DEBUG_OBJECTS
                flags |= gc.DEBUG_STATS
            gc.set_debug(flags)
            gc.collect()

            print("Tracked objects:", len(gc.get_objects()))

    def maybe_print_objects(self):
        if debug:
            print("Tracked objects:", len(gc.get_objects()))

    def tearDown(self):
        gc.set_debug(0)

    def test_multi_collection(self):
        gc.collect()
        self.maybe_enable_debug()

        multi = pycurl.CurlMulti()
        t = []
        searches = []
        for a in range(100):
            curl = util.DefaultCurl()
            multi.add_handle(curl)
            t.append(curl)

            c_id = id(curl)
            searches.append(c_id)
        m_id = id(multi)
        searches.append(m_id)

        self.maybe_print_objects()

        for curl in t:
            curl.close()
            multi.remove_handle(curl)

        self.maybe_print_objects()

        del curl
        del t
        del multi

        self.maybe_print_objects()
        gc.collect()
        self.maybe_print_objects()

        objects = gc.get_objects()
        for search in searches:
            for object in objects:
                assert search != id(object)

    def test_multi_cycle(self):
        gc.collect()
        self.maybe_enable_debug()

        multi = pycurl.CurlMulti()
        t = []
        searches = []
        for a in range(100):
            curl = util.DefaultCurl()
            multi.add_handle(curl)
            t.append(curl)

            c_id = id(curl)
            searches.append(c_id)
        m_id = id(multi)
        searches.append(m_id)

        self.maybe_print_objects()

        del curl
        del t
        del multi

        self.maybe_print_objects()
        gc.collect()
        self.maybe_print_objects()

        objects = gc.get_objects()
        for search in searches:
            for object in objects:
                assert search != id(object)

    def test_share_collection(self):
        gc.collect()
        self.maybe_enable_debug()

        share = pycurl.CurlShare()
        t = []
        searches = []
        for a in range(100):
            curl = util.DefaultCurl()
            curl.setopt(curl.SHARE, share)
            t.append(curl)

            c_id = id(curl)
            searches.append(c_id)
        m_id = id(share)
        searches.append(m_id)

        self.maybe_print_objects()

        for curl in t:
            curl.unsetopt(curl.SHARE)
            curl.close()

        self.maybe_print_objects()

        del curl
        del t
        del share

        self.maybe_print_objects()
        gc.collect()
        self.maybe_print_objects()

        objects = gc.get_objects()
        for search in searches:
            for object in objects:
                assert search != id(object)

    def test_share_cycle(self):
        gc.collect()
        self.maybe_enable_debug()

        share = pycurl.CurlShare()
        t = []
        searches = []
        for a in range(100):
            curl = util.DefaultCurl()
            curl.setopt(curl.SHARE, share)
            t.append(curl)

            c_id = id(curl)
            searches.append(c_id)
        m_id = id(share)
        searches.append(m_id)

        self.maybe_print_objects()

        del curl
        del t
        del share

        self.maybe_print_objects()
        gc.collect()
        self.maybe_print_objects()

        objects = gc.get_objects()
        for search in searches:
            for object in objects:
                assert search != id(object)

    # basic check of reference counting (use a memory checker like valgrind)
    def test_reference_counting(self):
        c = util.DefaultCurl()
        m = pycurl.CurlMulti()
        m.add_handle(c)
        del m
        m = pycurl.CurlMulti()
        c.close()
        del m, c

    def test_cyclic_gc(self):
        gc.collect()
        c = util.DefaultCurl()
        c.m = pycurl.CurlMulti()
        c.m.add_handle(c)
        # create some nasty cyclic references
        c.c = c
        c.c.c1 = c
        c.c.c2 = c
        c.c.c3 = c.c
        c.c.c4 = c.m
        c.m.c = c
        c.m.m = c.m
        c.m.c = c
        # delete
        gc.collect()
        self.maybe_enable_debug()
        ##print gc.get_referrers(c)
        ##print gc.get_objects()
        #if opts.verbose >= 1:
            #print("Tracked objects:", len(gc.get_objects()))
        c_id = id(c)
        # The `del' below should delete these 4 objects:
        #   Curl + internal dict, CurlMulti + internal dict
        del c
        gc.collect()
        objects = gc.get_objects()
        for object in objects:
            assert id(object) != c_id
        #if opts.verbose >= 1:
            #print("Tracked objects:", len(gc.get_objects()))

    def test_refcounting_bug_in_reset(self):
        if sys.platform == 'win32':
            iters = 10000
        else:
            iters = 100000
            
        try:
            range_generator = xrange
        except NameError:
            range_generator = range
        # Ensure that the refcounting error in "reset" is fixed:
        for i in range_generator(iters):
            c = util.DefaultCurl()
            c.reset()
            c.close()

    def test_writefunction_collection(self):
        self.check_callback(pycurl.WRITEFUNCTION)

    def test_headerfunction_collection(self):
        self.check_callback(pycurl.HEADERFUNCTION)

    def test_readfunction_collection(self):
        self.check_callback(pycurl.READFUNCTION)

    def test_progressfunction_collection(self):
        self.check_callback(pycurl.PROGRESSFUNCTION)

    @util.min_libcurl(7, 32, 0)
    def test_xferinfofunction_collection(self):
        self.check_callback(pycurl.XFERINFOFUNCTION)

    def test_debugfunction_collection(self):
        self.check_callback(pycurl.DEBUGFUNCTION)

    def test_ioctlfunction_collection(self):
        self.check_callback(pycurl.IOCTLFUNCTION)

    def test_opensocketfunction_collection(self):
        self.check_callback(pycurl.OPENSOCKETFUNCTION)

    def test_seekfunction_collection(self):
        self.check_callback(pycurl.SEEKFUNCTION)

    # This is failing too much on appveyor
    @util.only_unix
    def check_callback(self, callback):
        # Note: extracting a context manager seems to result in
        # everything being garbage collected even if the C code
        # does not clear the callback
        object_count = 0
        gc.collect()
        object_count = len(gc.get_objects())

        c = util.DefaultCurl()
        c.setopt(callback, lambda x: True)
        del c

        gc.collect()
        new_object_count = len(gc.get_objects())
        # it seems that GC sometimes collects something that existed
        # before this test ran, GH issues #273/#274
        self.assertIn(new_object_count, (object_count, object_count-1))

    def test_postfields_unicode_memory_leak_gh252(self):
        # this test passed even before the memory leak was fixed,
        # not sure why.

        c = util.DefaultCurl()
        gc.collect()
        before_object_count = len(gc.get_objects())

        for i in range(100000):
            c.setopt(pycurl.POSTFIELDS, util.u('hello world'))

        gc.collect()
        after_object_count = len(gc.get_objects())
        self.assert_(after_object_count <= before_object_count + 1000, 'Grew from %d to %d objects' % (before_object_count, after_object_count))
        c.close()

    def test_form_bufferptr_memory_leak_gh267(self):
        c = util.DefaultCurl()
        gc.collect()
        before_object_count = len(gc.get_objects())

        for i in range(100000):
            c.setopt(pycurl.HTTPPOST, [
                # Newer versions of libcurl accept FORM_BUFFERPTR
                # without FORM_BUFFER and reproduce the memory leak;
                # libcurl 7.19.0 requires FORM_BUFFER to be given before
                # FORM_BUFFERPTR.
                ("post1", (pycurl.FORM_BUFFER, 'foo.txt', pycurl.FORM_BUFFERPTR, "data1")),
                ("post2", (pycurl.FORM_BUFFER, 'bar.txt', pycurl.FORM_BUFFERPTR, "data2")),
            ])

        gc.collect()
        after_object_count = len(gc.get_objects())
        self.assert_(after_object_count <= before_object_count + 1000, 'Grew from %d to %d objects' % (before_object_count, after_object_count))
        c.close()

    def do_data_refcounting(self, option):
        c = util.DefaultCurl()
        f = open(devnull, 'a+')
        c.setopt(option, f)
        ref = weakref.ref(f)
        del f
        gc.collect()
        assert ref()
        
        for i in range(100):
            assert ref()
            c.setopt(option, ref())
        gc.collect()
        assert ref()
        
        c.close()
        gc.collect()
        assert ref() is None

    def test_readdata_refcounting(self):
        self.do_data_refcounting(pycurl.READDATA)

    def test_writedata_refcounting(self):
        self.do_data_refcounting(pycurl.WRITEDATA)

    def test_writeheader_refcounting(self):
        self.do_data_refcounting(pycurl.WRITEHEADER)

    # Python < 3.5 cannot create weak references to functions
    @util.min_python(3, 5)
    def do_function_refcounting(self, option, method_name):
        c = util.DefaultCurl()
        f = open(devnull, 'a+')
        fn = getattr(f, method_name)
        c.setopt(option, fn)
        ref = weakref.ref(fn)
        del f, fn
        gc.collect()
        assert ref()
        
        for i in range(100):
            assert ref()
            c.setopt(option, ref())
        gc.collect()
        assert ref()
        
        c.close()
        gc.collect()
        assert ref() is None

    def test_readfunction_refcounting(self):
        self.do_function_refcounting(pycurl.READFUNCTION, 'read')

    def test_writefunction_refcounting(self):
        self.do_function_refcounting(pycurl.WRITEFUNCTION, 'write')

    def test_headerfunction_refcounting(self):
        self.do_function_refcounting(pycurl.HEADERFUNCTION, 'write')
