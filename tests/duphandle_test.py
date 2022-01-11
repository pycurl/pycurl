#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import pycurl
import unittest
import gc
import weakref
try:
    import json
except ImportError:
    import simplejson as json

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class DuphandleTest(unittest.TestCase):
    def setUp(self):
        self.orig = util.DefaultCurl()

    def test_duphandle_attribute_dict(self):
        self.orig.orig_attr = 'orig-value'
        # attribute dict should be copied - the *object*, not the reference
        dup = self.orig.duphandle()
        assert dup.orig_attr == 'orig-value'
        # cloned dict should be a separate object
        dup.dup_attr = 'dup-value'
        try:
            self.orig.dup_attr == 'does not exist'
        except AttributeError as error:
            assert 'trying to obtain a non-existing attribute: dup_attr' in str(error.args)
        else:
            self.fail('should have raised AttributeError')
        # dealloc self.orig - original dict is freed from memory
        self.orig.close()
        del self.orig
        # cloned dict should still exist
        assert dup.orig_attr == 'orig-value'
        assert dup.dup_attr == 'dup-value'
        dup.close()

    def slist_check(self, handle, value, persistance=True):
        body = util.BytesIO()
        handle.setopt(pycurl.WRITEFUNCTION, body.write)
        handle.setopt(pycurl.URL, 'http://%s:8380/header_utf8?h=x-test-header' % localhost)
        handle.perform()
        result = body.getvalue().decode('utf-8')
        assert (result == value) == persistance

    def slist_test(self, clear_func, *args):
        # new slist object is created with ref count = 1
        self.orig.setopt(pycurl.HTTPHEADER, ['x-test-header: orig-slist'])
        # ref is copied and object incref'ed
        dup1 = self.orig.duphandle()
        # slist object is decref'ed and ref set to null
        clear_func(*args)
        # null ref is copied - no effect
        dup2 = self.orig.duphandle()
        # check slist object persistance
        self.slist_check(dup1, 'orig-slist', True)
        self.slist_check(dup2, 'orig-slist', False)
        # check overwriting - orig slist is decref'ed to 0 and finally deallocated
        # util_curlslist_update() and util_curlslist_dealloc()
        dup1.setopt(pycurl.HTTPHEADER, ['x-test-header: dup-slist'])
        self.slist_check(dup1, 'dup-slist', True)
        # cleanup
        dup1.close()
        dup2.close()
        self.orig.close()

    def test_duphandle_slist_xdecref(self):
        # util_curl_xdecref()
        self.slist_test(self.orig.reset)

    def test_duphandle_slist_unsetopt(self):
        # util_curl_unsetopt()
        self.slist_test(self.orig.unsetopt, pycurl.HTTPHEADER)

    def httppost_check(self, handle, value, persistance=True):
        body = util.BytesIO()
        handle.setopt(pycurl.WRITEFUNCTION, body.write)
        handle.setopt(pycurl.URL, 'http://%s:8380/postfields' % localhost)
        handle.perform()
        result = json.loads(body.getvalue())
        assert (result == value) == persistance

    def httppost_test(self, clear_func, *args):
        self.orig.setopt(pycurl.HTTPPOST, [
            ('field', (pycurl.FORM_CONTENTS, 'orig-httppost')),
        ])
        dup1 = self.orig.duphandle()
        clear_func(*args)
        dup2 = self.orig.duphandle()
        self.httppost_check(dup1, {'field': 'orig-httppost'}, True)
        self.httppost_check(dup2, {'field': 'orig-httppost'}, False)
        # util_curlhttppost_update() and util_curlhttppost_dealloc()
        dup1.setopt(pycurl.HTTPPOST, [
            ('field', (pycurl.FORM_CONTENTS, 'dup-httppost')),
        ])
        self.httppost_check(dup1, {'field': 'dup-httppost'}, True)
        dup1.close()
        dup2.close()
        self.orig.close()

    def test_duphandle_httppost_xdecref(self):
        # util_curl_xdecref()
        self.httppost_test(self.orig.reset)

    def test_duphandle_httppost_unsetopt(self):
        # util_curl_unsetopt()
        self.httppost_test(self.orig.unsetopt, pycurl.HTTPPOST)

    def test_duphandle_references(self):
        body = util.BytesIO()
        def callback(data):
            body.write(data)
        callback_ref = weakref.ref(callback)
        # preliminary checks of gc and weakref working as expected
        assert gc.get_referrers(callback) == []
        assert callback_ref() is not None
        # setopt - callback ref is copied and callback incref'ed
        self.orig.setopt(pycurl.WRITEFUNCTION, callback)
        assert gc.get_referrers(callback) == [self.orig]
        # duphandle - callback ref is copied and callback incref'ed
        dup = self.orig.duphandle()
        assert set(gc.get_referrers(callback)) == {self.orig, dup}
        # dealloc self.orig and decref callback
        self.orig.close()
        del self.orig
        assert gc.get_referrers(callback) == [dup]
        # decref callback again - back to ref count = 1
        del callback
        assert callback_ref() is not None
        # check that callback object still exists and is invoked
        dup.setopt(pycurl.URL, 'http://%s:8380/success' % localhost)
        dup.perform()
        result = body.getvalue().decode('utf-8')
        assert result == 'success'
        # final decref - callback is deallocated
        dup.close()
        assert callback_ref() is None
