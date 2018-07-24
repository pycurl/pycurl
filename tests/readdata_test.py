#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import pycurl
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import sys
import os.path
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

    def read(self, size):
        assert len(self.data) <= size
        if not self.finished:
            self.finished = True
            return self.data
        else:
            # Nothing more to read
            return ""

FORM_SUBMISSION_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'form_submission.txt')

class ReaddataTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurl()

    def tearDown(self):
        self.curl.close()

    def test_readdata_object(self):
        d = DataProvider(POSTSTRING)
        self.curl.setopt(self.curl.URL, 'http://%s:8380/postfields' % localhost)
        self.curl.setopt(self.curl.POST, 1)
        self.curl.setopt(self.curl.POSTFIELDSIZE, len(POSTSTRING))
        self.curl.setopt(self.curl.READDATA, d)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()

        actual = json.loads(sio.getvalue().decode())
        self.assertEqual(POSTFIELDS, actual)

    def test_post_with_read_returning_bytes(self):
        self.check_bytes('world')

    def test_post_with_read_returning_bytes_with_nulls(self):
        self.check_bytes("wor\0ld")

    def test_post_with_read_returning_bytes_with_multibyte(self):
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
        self.curl.setopt(self.curl.READDATA, d)
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

    def check_unicode(self, poststring):
        assert type(poststring) == util.text_type
        d = DataProvider(poststring)

        self.curl.setopt(self.curl.URL, 'http://%s:8380/raw_utf8' % localhost)
        self.curl.setopt(self.curl.POST, 1)
        self.curl.setopt(self.curl.HTTPHEADER, ['Content-Type: application/octet-stream'])
        self.curl.setopt(self.curl.POSTFIELDSIZE, len(poststring))
        self.curl.setopt(self.curl.READDATA, d)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()

        # json should be ascii
        actual = json.loads(sio.getvalue().decode('ascii'))
        self.assertEqual(poststring, actual)

    def test_readdata_file_binary(self):
        # file opened in binary mode
        f = open(FORM_SUBMISSION_PATH, 'rb')
        try:
            self.curl.setopt(self.curl.URL, 'http://%s:8380/postfields' % localhost)
            self.curl.setopt(self.curl.POST, 1)
            self.curl.setopt(self.curl.POSTFIELDSIZE, os.stat(FORM_SUBMISSION_PATH).st_size)
            self.curl.setopt(self.curl.READDATA, f)
            sio = util.BytesIO()
            self.curl.setopt(pycurl.WRITEDATA, sio)
            self.curl.perform()

            actual = json.loads(sio.getvalue().decode())
            self.assertEqual({'foo': 'bar'}, actual)
        finally:
            f.close()

    def test_readdata_file_text(self):
        # file opened in text mode
        f = open(FORM_SUBMISSION_PATH, 'rt')
        try:
            self.curl.setopt(self.curl.URL, 'http://%s:8380/postfields' % localhost)
            self.curl.setopt(self.curl.POST, 1)
            self.curl.setopt(self.curl.POSTFIELDSIZE, os.stat(FORM_SUBMISSION_PATH).st_size)
            self.curl.setopt(self.curl.READDATA, f)
            sio = util.BytesIO()
            self.curl.setopt(pycurl.WRITEDATA, sio)
            self.curl.perform()

            actual = json.loads(sio.getvalue().decode())
            self.assertEqual({'foo': 'bar'}, actual)
        finally:
            f.close()

    def test_readdata_file_like(self):
        data = 'hello=world'
        data_provider = DataProvider(data)
        self.curl.setopt(self.curl.URL, 'http://%s:8380/postfields' % localhost)
        self.curl.setopt(self.curl.POST, 1)
        self.curl.setopt(self.curl.POSTFIELDSIZE, len(data))
        self.curl.setopt(self.curl.READDATA, data_provider)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEDATA, sio)
        self.curl.perform()

        actual = json.loads(sio.getvalue().decode())
        self.assertEqual({'hello': 'world'}, actual)

    def test_readdata_and_readfunction_file_like(self):
        data = 'hello=world'
        data_provider = DataProvider(data)
        # data must be the same length
        function_provider = DataProvider('aaaaa=bbbbb')
        self.curl.setopt(self.curl.URL, 'http://%s:8380/postfields' % localhost)
        self.curl.setopt(self.curl.POST, 1)
        self.curl.setopt(self.curl.POSTFIELDSIZE, len(data))
        self.curl.setopt(self.curl.READDATA, data_provider)
        self.curl.setopt(self.curl.READFUNCTION, function_provider.read)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEDATA, sio)
        self.curl.perform()

        actual = json.loads(sio.getvalue().decode())
        self.assertEqual({'aaaaa': 'bbbbb'}, actual)

    def test_readfunction_and_readdata_file_like(self):
        data = 'hello=world'
        data_provider = DataProvider(data)
        # data must be the same length
        function_provider = DataProvider('aaaaa=bbbbb')
        self.curl.setopt(self.curl.URL, 'http://%s:8380/postfields' % localhost)
        self.curl.setopt(self.curl.POST, 1)
        self.curl.setopt(self.curl.POSTFIELDSIZE, len(data))
        self.curl.setopt(self.curl.READFUNCTION, function_provider.read)
        self.curl.setopt(self.curl.READDATA, data_provider)
        sio = util.BytesIO()
        self.curl.setopt(pycurl.WRITEDATA, sio)
        self.curl.perform()

        actual = json.loads(sio.getvalue().decode())
        self.assertEqual({'hello': 'world'}, actual)

    def test_readdata_and_readfunction_real_file(self):
        # data must be the same length
        with open(FORM_SUBMISSION_PATH) as f:
            function_provider = DataProvider('aaa=bbb')
            self.curl.setopt(self.curl.URL, 'http://%s:8380/postfields' % localhost)
            self.curl.setopt(self.curl.POST, 1)
            self.curl.setopt(self.curl.POSTFIELDSIZE, os.stat(FORM_SUBMISSION_PATH).st_size)
            self.curl.setopt(self.curl.READDATA, f)
            self.curl.setopt(self.curl.READFUNCTION, function_provider.read)
            sio = util.BytesIO()
            self.curl.setopt(pycurl.WRITEDATA, sio)
            self.curl.perform()

            actual = json.loads(sio.getvalue().decode())
            self.assertEqual({'aaa': 'bbb'}, actual)

    def test_readfunction_and_readdata_real_file(self):
        # data must be the same length
        with open(FORM_SUBMISSION_PATH) as f:
            function_provider = DataProvider('aaa=bbb')
            self.curl.setopt(self.curl.URL, 'http://%s:8380/postfields' % localhost)
            self.curl.setopt(self.curl.POST, 1)
            self.curl.setopt(self.curl.POSTFIELDSIZE, os.stat(FORM_SUBMISSION_PATH).st_size)
            self.curl.setopt(self.curl.READFUNCTION, function_provider.read)
            self.curl.setopt(self.curl.READDATA, f)
            sio = util.BytesIO()
            self.curl.setopt(pycurl.WRITEDATA, sio)
            self.curl.perform()

            actual = json.loads(sio.getvalue().decode())
            self.assertEqual({'foo': 'bar'}, actual)

    def test_readdata_not_file_like(self):
        not_file_like = object()
        try:
            self.curl.setopt(self.curl.READDATA, not_file_like)
        except TypeError as exc:
            self.assertIn('object given without a read method', str(exc))
        else:
            self.fail('TypeError not raised')
