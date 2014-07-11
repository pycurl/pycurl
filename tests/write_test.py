#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import unittest
import pycurl
import tempfile
import shutil
import os.path

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class Acceptor(object):
    def __init__(self):
        self.buffer = ''
    
    def write(self, chunk):
        self.buffer += chunk.decode()

class WriteTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_write_to_tempfile_via_function(self):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/success')
        f = tempfile.NamedTemporaryFile()
        try:
            self.curl.setopt(pycurl.WRITEFUNCTION, f.write)
            self.curl.perform()
            f.seek(0)
            body = f.read()
        finally:
            f.close()
        self.assertEqual('success', body.decode())
    
    @util.only_python3
    def test_write_to_tempfile_via_object(self):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/success')
        f = tempfile.NamedTemporaryFile()
        try:
            self.curl.setopt(pycurl.WRITEDATA, f)
            self.curl.perform()
            f.seek(0)
            body = f.read()
        finally:
            f.close()
        self.assertEqual('success', body.decode())
    
    def test_write_to_file_via_function(self):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/success')
        dir = tempfile.mkdtemp()
        try:
            path = os.path.join(dir, 'pycurltest')
            f = open(path, 'wb+')
            try:
                self.curl.setopt(pycurl.WRITEFUNCTION, f.write)
                self.curl.perform()
                f.seek(0)
                body = f.read()
            finally:
                f.close()
        finally:
            shutil.rmtree(dir)
        self.assertEqual('success', body.decode())
    
    def test_write_to_file_via_object(self):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/success')
        dir = tempfile.mkdtemp()
        try:
            path = os.path.join(dir, 'pycurltest')
            f = open(path, 'wb+')
            try:
                self.curl.setopt(pycurl.WRITEDATA, f)
                self.curl.perform()
                f.seek(0)
                body = f.read()
            finally:
                f.close()
        finally:
            shutil.rmtree(dir)
        self.assertEqual('success', body.decode())
    
    def test_write_to_file_like(self):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/success')
        acceptor = Acceptor()
        self.curl.setopt(pycurl.WRITEDATA, acceptor)
        self.curl.perform()
        self.assertEqual('success', acceptor.buffer)
