#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import pycurl
import unittest
import sys
try:
    import json
except ImportError:
    import simplejson as json
try:
    import urllib.parse as urllib_parse
except ImportError:
    import urllib as urllib_parse

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

POSTFIELDS = {
    'field1':'value1',
    'field2':'value2 with blanks',
    'field3':'value3',
}
POSTSTRING = urllib_parse.urlencode(POSTFIELDS)

class DataProvider(object):
    def __init__(self, data):
        self.data = data
        self.finished = False

    def read_cb(self, size):
        assert len(self.data) <= size
        if not self.finished:
            self.finished = True
            return self.data
        else:
            # Nothing more to read
            return ""

class ReadCbTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurl()

    def tearDown(self):
        self.curl.close()

    def test_post_with_read_callback(self):
        d = DataProvider(POSTSTRING)
        self.curl.setopt(self.curl.URL, 'http://%s:8380/postfields' % localhost)
        self.curl.setopt(self.curl.POST, 1)
        self.curl.setopt(self.curl.POSTFIELDSIZE, len(POSTSTRING))
        self.curl.setopt(self.curl.READFUNCTION, d.read_cb)
        #self.curl.setopt(self.curl.VERBOSE, 1)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()

        actual = json.loads(sio.getvalue().decode())
        self.assertEqual(POSTFIELDS, actual)

    def test_post_with_read_callback_returning_bytes(self):
        self.check_bytes('world')

    def test_post_with_read_callback_returning_bytes_with_nulls(self):
        self.check_bytes("wor\0ld")

    def test_post_with_read_callback_returning_bytes_with_multibyte(self):
        self.check_bytes(util.u("Пушкин"))

    def check_bytes(self, poststring):
        data = poststring.encode('utf8')
        assert type(data) == util.binary_type
        d = DataProvider(data)

        self.curl.setopt(self.curl.URL, 'http://%s:8380/raw_utf8' % localhost)
        self.curl.setopt(self.curl.POST, 1)
        self.curl.setopt(self.curl.HTTPHEADER, ['Content-Type: application/octet-stream'])
        # length of bytes
        self.curl.setopt(self.curl.POSTFIELDSIZE, len(data))
        self.curl.setopt(self.curl.READFUNCTION, d.read_cb)
        #self.curl.setopt(self.curl.VERBOSE, 1)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()

        # json should be ascii
        actual = json.loads(sio.getvalue().decode('ascii'))
        self.assertEqual(poststring, actual)

    def test_post_with_read_callback_returning_memoryview(self):
        self.check_memoryview('world')

    def test_post_with_read_callback_returning_memoryview_with_nulls(self):
        self.check_memoryview("wor\0ld")

    def test_post_with_read_callback_returning_memoryview_with_multibyte(self):
        self.check_memoryview(util.u("Пушкин"))

    def check_memoryview(self, poststring):
        data = memoryview(poststring.encode('utf8'))
        assert type(data) == memoryview
        d = DataProvider(data)

        self.curl.setopt(self.curl.URL, 'http://%s:8380/raw_utf8' % localhost)
        self.curl.setopt(self.curl.POST, 1)
        self.curl.setopt(self.curl.HTTPHEADER, ['Content-Type: application/octet-stream'])
        # length of bytes
        self.curl.setopt(self.curl.POSTFIELDSIZE, len(data))
        self.curl.setopt(self.curl.READFUNCTION, d.read_cb)
        #self.curl.setopt(self.curl.VERBOSE, 1)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()

        # json should be ascii
        actual = json.loads(sio.getvalue().decode('ascii'))
        self.assertEqual(poststring, actual)

    def test_post_with_read_callback_returning_unicode(self):
        self.check_unicode(util.u('world'))

    def test_post_with_read_callback_returning_unicode_with_nulls(self):
        self.check_unicode(util.u("wor\0ld"))

    def test_post_with_read_callback_returning_unicode_with_multibyte(self):
        try:
            self.check_unicode(util.u("Пушкин"))
            # prints:
            # UnicodeEncodeError: 'ascii' codec can't encode characters in position 6-11: ordinal not in range(128)
        except pycurl.error:
            err, msg = sys.exc_info()[1].args
            # we expect pycurl.E_WRITE_ERROR as the response
            self.assertEqual(pycurl.E_ABORTED_BY_CALLBACK, err)
            self.assertEqual('operation aborted by callback', msg)

    def test_post_with_read_callback_pause(self):
        data = b"field1=value1"
        paused = False
        resumed = False
        offset = 0

        def read_cb(size):
            nonlocal paused, offset
            if not paused:
                paused = True
                return pycurl.READFUNC_PAUSE
            if offset < len(data):
                take = min(size, len(data) - offset)
                chunk = data[offset : offset + take]
                offset += len(chunk)
                return chunk
            return b""

        self.curl.setopt(self.curl.URL, 'http://%s:8380/raw_utf8' % localhost)
        self.curl.setopt(self.curl.POST, 1)
        self.curl.setopt(self.curl.HTTPHEADER, ['Content-Type: application/octet-stream'])
        self.curl.setopt(self.curl.POSTFIELDSIZE, len(data))
        self.curl.setopt(self.curl.READFUNCTION, read_cb)
        #self.curl.setopt(self.curl.VERBOSE, 1)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)

        multi = pycurl.CurlMulti()
        err_list = []
        multi.add_handle(self.curl)
        running = True
        while running:
            _, running = multi.perform()
            if paused and not resumed:
                resumed = True
                self.curl.pause(pycurl.PAUSE_CONT)
            if running:
                multi.select(0.1)
        while True:
            queued, _, err = multi.info_read()
            if err:
                err_list.extend(err)
            if not queued:
                break

        self.assertFalse(err_list)
        self.assertTrue(resumed)

    def check_unicode(self, poststring):
        assert type(poststring) == util.text_type
        d = DataProvider(poststring)

        self.curl.setopt(self.curl.URL, 'http://%s:8380/raw_utf8' % localhost)
        self.curl.setopt(self.curl.POST, 1)
        self.curl.setopt(self.curl.HTTPHEADER, ['Content-Type: application/octet-stream'])
        self.curl.setopt(self.curl.POSTFIELDSIZE, len(poststring))
        self.curl.setopt(self.curl.READFUNCTION, d.read_cb)
        #self.curl.setopt(self.curl.VERBOSE, 1)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()

        # json should be ascii
        actual = json.loads(sio.getvalue().decode('ascii'))
        self.assertEqual(poststring, actual)

    def test_post_with_read_callback_returning_non_buffer(self):
        def read_cb(size):
            return object()

        self.check_bad_read_callback(read_cb)

    def test_post_with_read_callback_returning_overly_large_buffer(self):
        def read_cb(size):
            return " " * (size + 1)

        self.check_bad_read_callback(read_cb, post_len=1)

    def test_post_with_read_callback_that_throws(self):
        def read_cb(size):
            raise RuntimeError("Boom")

        self.check_bad_read_callback(read_cb)

    def test_post_with_read_callback_that_aborts(self):
        def read_cb(size):
            return pycurl.READFUNC_ABORT

        self.check_bad_read_callback(read_cb)

    def test_post_with_read_callback_that_returns_bad_integer(self):
        def read_cb(size):
            return 5000

        self.check_bad_read_callback(read_cb)

    def test_post_with_read_callback_taking_incorrect_args(self):
        def read_cb(too, many, args):
            pass

        self.check_bad_read_callback(read_cb)

    def test_post_with_read_callback_not_callable(self):
        with self.assertRaises(TypeError):
            self.curl.setopt(self.curl.READFUNCTION, object())

    def check_bad_read_callback(self, read_cb, post_len=16, expect_code=pycurl.E_ABORTED_BY_CALLBACK):
        self.curl.setopt(self.curl.URL, 'http://%s:8380/raw_utf8' % localhost)
        self.curl.setopt(self.curl.POST, 1)
        self.curl.setopt(self.curl.HTTPHEADER, ['Content-Type: application/octet-stream'])
        self.curl.setopt(self.curl.POSTFIELDSIZE, post_len)
        self.curl.setopt(self.curl.READFUNCTION, read_cb)
        # self.curl.setopt(self.curl.VERBOSE, 1)

        with self.assertRaises(pycurl.error) as context:
            self.curl.perform()

        err, msg = context.exception.args
        self.assertEqual(expect_code, err)

    def test_readfunction_unsetopt(self):
        self.curl.setopt(self.curl.URL, 'http://%s:8380/raw_utf8' % localhost)
        self.curl.setopt(self.curl.POST, 1)
        # Body is not read unless HTTP Expect is disabled
        self.curl.setopt(self.curl.HTTPHEADER, ['Content-Type: application/octet-stream', 'Expect: '])
        self.curl.setopt(self.curl.READFUNCTION, None)
        #self.curl.setopt(self.curl.VERBOSE, 1)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)

        self.curl.perform()
        # did not crash
