#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import pytest
import pycurl
import unittest

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

# NB: HTTP RFC requires headers to be latin1 encoded, which we violate.
# See the comments under /header_utf8 route in app.py.

class HeaderTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurl()

    def tearDown(self):
        self.curl.close()

    def test_ascii_string_header(self):
        self.check('x-test-header: ascii', 'ascii')

    def test_ascii_unicode_header(self):
        self.check(util.u('x-test-header: ascii'), 'ascii')

    # on python 2 unicode is accepted in strings because strings are byte strings
    @util.only_python3
    def test_unicode_string_header(self):
        with pytest.raises(UnicodeEncodeError):
            self.check('x-test-header: Москва', 'Москва')

    def test_unicode_unicode_header(self):
        with pytest.raises(UnicodeEncodeError):
            self.check(util.u('x-test-header: Москва'), util.u('Москва'))

    def test_encoded_unicode_header(self):
        self.check(util.u('x-test-header: Москва').encode('utf-8'), util.u('Москва'))

    def check(self, send, expected):
        # check as list and as tuple, because they may be handled differently
        self.do_check([send], expected)
        self.do_check((send,), expected)

    def do_check(self, send, expected):
        self.curl.setopt(pycurl.URL, 'http://%s:8380/header_utf8?h=x-test-header' % localhost)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.setopt(pycurl.HTTPHEADER, send)
        self.curl.perform()
        self.assertEqual(expected, sio.getvalue().decode('utf-8'))
