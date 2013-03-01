#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et

import os
import sys
import tempfile
import pycurl
import unittest
import io
try:
    from cStringIO import StringIO
except ImportError:
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO

from . import app
from . import runwsgi

setup_module, teardown_module = runwsgi.app_runner_setup((app.app, 8380))

class RequestTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_perform_get(self):
        # This test performs a GET request without doing anything else.
        # Unfortunately, the default curl behavior is to print response
        # body to standard output, which spams test output.
        # As a result this test is commented out. Uncomment for debugging.
        # test_perform_get_with_default_write_function is the test
        # which exercises default curl write handler.
        return
        
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/success')
        self.curl.perform()
    
    def test_perform_get_with_write_function(self):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/success')
        sio = StringIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, sio.write)
        self.curl.perform()
        self.assertEqual('success', sio.getvalue())
    
    def test_perform_get_with_default_write_function(self):
        self.curl.setopt(pycurl.URL, 'http://localhost:8380/success')
        #with tempfile.NamedTemporaryFile() as f:
        with open('w', 'w+') as f:
            # nose output capture plugin replaces sys.stdout with a StringIO
            # instance. We want to redirect the underlying file descriptor
            # anyway because underlying C code uses it.
            # But keep track of whether we replace sys.stdout.
            perform_dup = False
            if hasattr(sys.stdout, 'fileno'):
                try:
                    sys.stdout.fileno()
                    perform_dup = True
                except io.UnsupportedOperation:
                    # stdout is a StringIO
                    pass
            if perform_dup:
                saved_stdout_fd = os.dup(sys.stdout.fileno())
                os.dup2(f.fileno(), sys.stdout.fileno())
            else:
                saved_stdout = sys.stdout
                sys.stdout = f
            try:
                self.curl.perform()
            finally:
                sys.stdout.flush()
                if perform_dup:
                    os.fsync(sys.stdout.fileno())
                    os.dup2(saved_stdout_fd, sys.stdout.fileno())
                    os.close(saved_stdout_fd)
                else:
                    sys.stdout = saved_stdout
            f.seek(0)
            body = f.read()
        self.assertEqual('success', body)
