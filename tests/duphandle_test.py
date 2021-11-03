#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import pycurl
import unittest
try:
    import json
except ImportError:
    import simplejson as json

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class DuphandleTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurl()
        self.dup = None

    def tearDown(self):
        if self.dup:
            self.dup.close()

    def test_duphandle_attribute_dict(self):
        self.curl.original_attr = 'original-value'
        # attribute dict should be copied - the *object*, not the reference
        self.dup = self.curl.duphandle()
        assert self.dup.original_attr == 'original-value'
        # cloned dict should be a separate object
        self.dup.clone_attr = 'clone-value'
        try:
            self.curl.clone_attr == 'does not exist'
        except AttributeError as error:
            assert 'trying to obtain a non-existing attribute: clone_attr' in str(error.args)
        else:
            self.fail('should have raised AttributeError')
        # decref - original dict is freed from memory
        self.curl.close()
        del self.curl
        # cloned dict should still exist
        assert self.dup.original_attr == 'original-value'
        assert self.dup.clone_attr == 'clone-value'

    def test_duphandle_slist(self):
        self.curl.setopt(pycurl.HTTPHEADER, ['x-test-header: original-slist'])
        # slist *reference* should be copied and incremented
        self.dup = self.curl.duphandle()
        # decref
        self.curl.close()
        del self.curl
        # slist object should still exist
        body = util.BytesIO()
        self.dup.setopt(pycurl.WRITEFUNCTION, body.write)
        self.dup.setopt(pycurl.URL, 'http://%s:8380/header_utf8?h=x-test-header' % localhost)
        self.dup.perform()
        result = body.getvalue().decode('utf-8')
        assert result == 'original-slist'

    def test_duphandle_httppost(self):
        self.curl.setopt(pycurl.HTTPPOST, [
            ('field', (pycurl.FORM_CONTENTS, 'original-httppost')),
        ])
        # httppost *reference* should be copied and incremented
        self.dup = self.curl.duphandle()
        # decref
        self.curl.close()
        del self.curl
        # httppost object should still exist
        body = util.BytesIO()
        self.dup.setopt(pycurl.WRITEFUNCTION, body.write)
        self.dup.setopt(pycurl.URL, 'http://%s:8380/postfields' % localhost)
        self.dup.perform()
        result = json.loads(body.getvalue())
        assert result == {'field': 'original-httppost'}

    def test_duphandle_callback(self):
        body = util.BytesIO()
        def callback(data):
            body.write(data)
        self.curl.setopt(pycurl.WRITEFUNCTION, callback)
        # callback *reference* should be copied and incremented
        self.dup = self.curl.duphandle()
        # decref
        self.curl.close()
        del self.curl
        del callback
        # callback object should still exist
        self.dup.setopt(pycurl.URL, 'http://%s:8380/success' % localhost)
        self.dup.perform()
        result = body.getvalue().decode('utf-8')
        assert result == 'success'
