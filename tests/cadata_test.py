#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import os
import pycurl
import unittest

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8384, dict(ssl=True)))

class CaCertsTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurlLocalhost(8384)

    def tearDown(self):
        self.curl.close()

    @util.only_ssl_backends('openssl')
    def test_request_with_verifypeer(self):
        with open(os.path.join(os.path.dirname(__file__), 'certs', 'ca.crt'), 'rb') as stream:
            cadata = stream.read().decode('ASCII')
        self.curl.setopt(pycurl.URL, 'https://localhost:8384/success')
        sio = util.BytesIO()
        self.curl.set_ca_certs(cadata)
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        # self signed certificate, but ca cert should be loaded
        self.curl.setopt(pycurl.SSL_VERIFYPEER, 1)
        self.curl.perform()
        assert sio.getvalue().decode() == 'success'

    @util.only_ssl_backends('openssl')
    def test_set_ca_certs_bytes(self):
        self.curl.set_ca_certs(util.b('hello world\x02\xe0'))

    @util.only_ssl_backends('openssl')
    def test_set_ca_certs_bogus_type(self):
        try:
            self.curl.set_ca_certs(42)
        except TypeError as e:
            self.assertEqual('set_ca_certs argument must be a byte string or a Unicode string with ASCII code points only', str(e))
