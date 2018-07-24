#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import pycurl
import unittest

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class DebugTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurl()
        self.debug_entries = []

    def tearDown(self):
        self.curl.close()

    def debug_function(self, t, b):
        self.debug_entries.append((t, b))

    def test_perform_get_with_debug_function(self):
        self.curl.setopt(pycurl.VERBOSE, 1)
        self.curl.setopt(pycurl.DEBUGFUNCTION, self.debug_function)
        self.curl.setopt(pycurl.URL, 'http://%s:8380/success' % localhost)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()

        # Some checks with no particular intent
        self.check(0, util.b('Trying'))
        if util.pycurl_version_less_than(7, 24):
            self.check(0, util.b('connected'))
        else:
            self.check(0, util.b('Connected to %s' % localhost))
        self.check(0, util.b('port 8380'))
        # request
        self.check(2, util.b('GET /success HTTP/1.1'))
        # response
        self.check(1, util.b('HTTP/1.0 200 OK'))
        self.check(1, util.b('Content-Length: 7'))
        # result
        self.check(3, util.b('success'))

    # test for #210
    def test_debug_unicode(self):
        self.curl.setopt(pycurl.VERBOSE, 1)
        self.curl.setopt(pycurl.DEBUGFUNCTION, self.debug_function)
        self.curl.setopt(pycurl.URL, 'http://%s:8380/utf8_body' % localhost)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()

        # 3 = response body
        search = util.b('\xd0\x94\xd1\x80\xd1\x83\xd0\xb6\xd0\xb1\xd0\xb0 \xd0\xbd\xd0\xb0\xd1\x80\xd0\xbe\xd0\xb4\xd0\xbe\xd0\xb2').decode('utf8')
        self.check(3, search.encode('utf8'))

    def check(self, wanted_t, wanted_b):
        for t, b in self.debug_entries:
            if t == wanted_t and wanted_b in b:
                return
        assert False, "%d: %s not found in debug entries\nEntries are:\n%s" % \
            (wanted_t, repr(wanted_b), repr(self.debug_entries))
