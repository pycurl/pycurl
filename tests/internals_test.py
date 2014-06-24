#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest
try:
    import cPickle
except ImportError:
    cPickle = None
import pickle
import copy

from . import util

class InternalsTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
        del self.curl
    
    # /***********************************************************************
    # // test misc
    # ************************************************************************/
    
    def test_constant_aliasing(self):
        assert self.curl.URL is pycurl.URL
    
    # /***********************************************************************
    # // test handles
    # ************************************************************************/

    def test_remove_invalid_handle(self):
        m = pycurl.CurlMulti()
        try:
            m.remove_handle(self.curl)
        except pycurl.error:
            pass
        else:
            assert False, "No exception when trying to remove a handle that is not in CurlMulti"
        del m
    
    def test_remove_invalid_closed_handle(self):
        m = pycurl.CurlMulti()
        c = pycurl.Curl()
        c.close()
        m.remove_handle(c)
        del m, c
    
    def test_add_closed_handle(self):
        m = pycurl.CurlMulti()
        c = pycurl.Curl()
        c.close()
        try:
            m.add_handle(c)
        except pycurl.error:
            pass
        else:
            assert 0, "No exception when trying to add a close handle to CurlMulti"
        m.close()
        del m, c
    
    def test_add_handle_twice(self):
        m = pycurl.CurlMulti()
        m.add_handle(self.curl)
        try:
            m.add_handle(self.curl)
        except pycurl.error:
            pass
        else:
            assert 0, "No exception when trying to add the same handle twice"
        del m
    
    def test_add_handle_on_multiple_stacks(self):
        m1 = pycurl.CurlMulti()
        m2 = pycurl.CurlMulti()
        m1.add_handle(self.curl)
        try:
            m2.add_handle(self.curl)
        except pycurl.error:
            pass
        else:
            assert 0, "No exception when trying to add the same handle on multiple stacks"
        del m1, m2
    
    def test_move_handle(self):
        m1 = pycurl.CurlMulti()
        m2 = pycurl.CurlMulti()
        m1.add_handle(self.curl)
        m1.remove_handle(self.curl)
        m2.add_handle(self.curl)
        del m1, m2
    
    # /***********************************************************************
    # // test copying and pickling - copying and pickling of
    # // instances of Curl and CurlMulti is not allowed
    # ************************************************************************/

    def test_copy_curl(self):
        try:
            copy.copy(self.curl)
        # python 2 raises copy.Error, python 3 raises TypeError
        except (copy.Error, TypeError):
            pass
        else:
            assert False, "No exception when trying to copy a Curl handle"
    
    def test_copy_multi(self):
        m = pycurl.CurlMulti()
        try:
            copy.copy(m)
        except (copy.Error, TypeError):
            pass
        else:
            assert False, "No exception when trying to copy a CurlMulti handle"
    
    def test_copy_multi(self):
        s = pycurl.CurlShare()
        try:
            copy.copy(s)
        except (copy.Error, TypeError):
            pass
        else:
            assert False, "No exception when trying to copy a CurlShare handle"
    
    def test_pickle_curl(self):
        fp = util.StringIO()
        p = pickle.Pickler(fp, 1)
        try:
            p.dump(self.curl)
        # python 2 raises pickle.PicklingError, python 3 raises TypeError
        except (pickle.PicklingError, TypeError):
            pass
        else:
            assert 0, "No exception when trying to pickle a Curl handle"
        del fp, p
    
    def test_pickle_multi(self):
        m = pycurl.CurlMulti()
        fp = util.StringIO()
        p = pickle.Pickler(fp, 1)
        try:
            p.dump(m)
        except (pickle.PicklingError, TypeError):
            pass
        else:
            assert 0, "No exception when trying to pickle a CurlMulti handle"
        del m, fp, p
    
    def test_pickle_share(self):
        s = pycurl.CurlShare()
        fp = util.StringIO()
        p = pickle.Pickler(fp, 1)
        try:
            p.dump(s)
        except (pickle.PicklingError, TypeError):
            pass
        else:
            assert 0, "No exception when trying to pickle a CurlShare handle"
        del s, fp, p
    
    def test_pickle_dumps_curl(self):
        try:
            pickle.dumps(self.curl)
        # python 2 raises pickle.PicklingError, python 3 raises TypeError
        except (pickle.PicklingError, TypeError):
            pass
        else:
            self.fail("No exception when trying to pickle a Curl handle")
    
    def test_pickle_dumps_multi(self):
        m = pycurl.CurlMulti()
        try:
            pickle.dumps(m)
        except (pickle.PicklingError, TypeError):
            pass
        else:
            self.fail("No exception when trying to pickle a CurlMulti handle")
    
    def test_pickle_dumps_share(self):
        s = pycurl.CurlShare()
        try:
            pickle.dumps(s)
        except (pickle.PicklingError, TypeError):
            pass
        else:
            self.fail("No exception when trying to pickle a CurlShare handle")
    
    if cPickle is not None:
        def test_cpickle_curl(self):
            fp = util.StringIO()
            p = cPickle.Pickler(fp, 1)
            try:
                p.dump(self.curl)
            except cPickle.PicklingError:
                pass
            else:
                assert 0, "No exception when trying to pickle a Curl handle via cPickle"
            del fp, p
        
        def test_cpickle_multi(self):
            m = pycurl.CurlMulti()
            fp = util.StringIO()
            p = cPickle.Pickler(fp, 1)
            try:
                p.dump(m)
            except cPickle.PicklingError:
                pass
            else:
                assert 0, "No exception when trying to pickle a CurlMulti handle via cPickle"
            del m, fp, p
        
        def test_cpickle_share(self):
            s = pycurl.CurlMulti()
            fp = util.StringIO()
            p = cPickle.Pickler(fp, 1)
            try:
                p.dump(s)
            except cPickle.PicklingError:
                pass
            else:
                assert 0, "No exception when trying to pickle a CurlShare handle via cPickle"
            del s, fp, p
