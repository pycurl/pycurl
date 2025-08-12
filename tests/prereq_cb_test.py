#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import sys
import unittest
import pycurl

from . import util
from . import appmanager

setup_module, teardown_module = appmanager.setup(('app', 8380))

class PrereqCbTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurl()
        self.curl.setopt(self.curl.URL, 'http://%s:8380/success' % localhost)
        self.curl.setopt(pycurl.FORBID_REUSE, True)

    def tearDown(self):
        self.curl.close()

    @util.min_libcurl(7, 80, 0)
    def test_prereqfunction_ok(self):
        called = {}

        def prereqfunction(conn_primary_ip, conn_local_ip, conn_primary_port, conn_local_port):
            called['called'] = True
            called['conn_primary_ip'] = conn_primary_ip
            called['conn_local_ip'] = conn_local_ip
            called['conn_primary_port'] = conn_primary_port
            called['conn_local_port'] = conn_local_port
            return pycurl.PREREQFUNC_OK

        self.curl.setopt(pycurl.PREREQFUNCTION, prereqfunction)
        self.curl.perform()

        assert called['called']
        self.assertEqual(called['conn_primary_ip'], '127.0.0.1')
        self.assertEqual(called['conn_local_ip'], '127.0.0.1')
        self.assertEqual(called['conn_primary_port'], 8380)
        self.assertEqual(type(called['conn_local_port']), int)

    @util.min_libcurl(7, 80, 0)
    def test_prereqfunction_fail(self):
        called = {}

        def prereqfunction(conn_primary_ip, conn_local_ip, conn_primary_port, conn_local_port):
            called['called'] = True
            return pycurl.PREREQFUNC_ABORT

        self.curl.setopt(pycurl.PREREQFUNCTION, prereqfunction)

        try:
            self.curl.perform()
        except pycurl.error:
            err, msg = sys.exc_info()[1].args
            self.assertEqual(pycurl.E_ABORTED_BY_CALLBACK, err)
            self.assertEqual('operation aborted by pre-request callback', msg)
            
        assert called['called']

    @util.min_libcurl(7, 80, 0)
    def test_prereqfunction_bogus_return(self):
        called = {}

        def prereqfunction(conn_primary_ip, conn_local_ip, conn_primary_port, conn_local_port):
            called['called'] = True
            return 'bogus'

        self.curl.setopt(pycurl.PREREQFUNCTION, prereqfunction)

        try:
            self.curl.perform()
        except pycurl.error:
            err, msg = sys.exc_info()[1].args
            self.assertEqual(pycurl.E_ABORTED_BY_CALLBACK, err)
            self.assertEqual('operation aborted by pre-request callback', msg)

        assert called['called']

class PrereqCbUnsetTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurl()

    @util.min_libcurl(7, 80, 0)
    def test_prereqfunction_none(self):
        self.curl.setopt(pycurl.PREREQFUNCTION, None)

    @util.min_libcurl(7, 80, 0)
    def test_prereqfunction_unset(self):
        self.curl.unsetopt(pycurl.PREREQFUNCTION)
