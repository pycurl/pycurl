#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import nose
import unittest
import pycurl

from . import util

sftp_server = 'sftp://web.sourceforge.net'

@nose.plugins.attrib.attr('online')
@nose.plugins.attrib.attr('ssh')
class SshKeyCbTest(unittest.TestCase):
    '''This test requires Internet access.'''

    def setUp(self):
        self.curl = util.DefaultCurl()
        self.curl.setopt(pycurl.URL, sftp_server)
        self.curl.setopt(pycurl.VERBOSE, True)

    def tearDown(self):
        self.curl.close()

    @util.min_libcurl(7, 19, 6)
    # curl compiled with libssh doesn't support
    # CURLOPT_SSH_KNOWNHOSTS and CURLOPT_SSH_KEYFUNCTION
    @util.guard_unknown_libcurl_option
    def test_keyfunction(self):
        # with keyfunction returning ok

        def keyfunction(known_key, found_key, match):
            return pycurl.KHSTAT_FINE

        self.curl.setopt(pycurl.SSH_KNOWNHOSTS, '.known_hosts')
        self.curl.setopt(pycurl.SSH_KEYFUNCTION, keyfunction)

        try:
            self.curl.perform()
            self.fail('should have raised')
        except pycurl.error as e:
            self.assertEqual(pycurl.E_LOGIN_DENIED, e.args[0])

        # with keyfunction returning not ok

        def keyfunction(known_key, found_key, match):
            return pycurl.KHSTAT_REJECT

        self.curl.setopt(pycurl.SSH_KNOWNHOSTS, '.known_hosts')
        self.curl.setopt(pycurl.SSH_KEYFUNCTION, keyfunction)

        try:
            self.curl.perform()
            self.fail('should have raised')
        except pycurl.error as e:
            self.assertEqual(pycurl.E_PEER_FAILED_VERIFICATION, e.args[0])

    @util.min_libcurl(7, 19, 6)
    @util.guard_unknown_libcurl_option
    def test_keyfunction_bogus_return(self):
        def keyfunction(known_key, found_key, match):
            return 'bogus'

        self.curl.setopt(pycurl.SSH_KNOWNHOSTS, '.known_hosts')
        self.curl.setopt(pycurl.SSH_KEYFUNCTION, keyfunction)

        try:
            self.curl.perform()
            self.fail('should have raised')
        except pycurl.error as e:
            self.assertEqual(pycurl.E_PEER_FAILED_VERIFICATION, e.args[0])


@nose.plugins.attrib.attr('ssh')
class SshKeyCbUnsetTest(unittest.TestCase):
    def setUp(self):
        self.curl = util.DefaultCurl()
        self.curl.setopt(pycurl.URL, sftp_server)
        self.curl.setopt(pycurl.VERBOSE, True)

    @util.min_libcurl(7, 19, 6)
    @util.guard_unknown_libcurl_option
    def test_keyfunction_none(self):
        self.curl.setopt(pycurl.SSH_KEYFUNCTION, None)

    @util.min_libcurl(7, 19, 6)
    @util.guard_unknown_libcurl_option
    def test_keyfunction_unset(self):
        self.curl.unsetopt(pycurl.SSH_KEYFUNCTION)
