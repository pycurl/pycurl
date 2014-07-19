#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest

from . import util

class ProtocolConstantsTest(unittest.TestCase):
    @util.min_libcurl(7, 19, 4)
    def test_7_19_4_protocols(self):
        assert hasattr(pycurl, 'PROTO_ALL')
        assert hasattr(pycurl, 'PROTO_DICT')
        assert hasattr(pycurl, 'PROTO_FILE')
        assert hasattr(pycurl, 'PROTO_FTP')
        assert hasattr(pycurl, 'PROTO_FTPS')
        assert hasattr(pycurl, 'PROTO_HTTP')
        assert hasattr(pycurl, 'PROTO_HTTPS')
        assert hasattr(pycurl, 'PROTO_LDAP')
        assert hasattr(pycurl, 'PROTO_LDAPS')
        assert hasattr(pycurl, 'PROTO_SCP')
        assert hasattr(pycurl, 'PROTO_SFTP')
        assert hasattr(pycurl, 'PROTO_TELNET')
        assert hasattr(pycurl, 'PROTO_TFTP')
    
    @util.min_libcurl(7, 20, 0)
    def test_7_20_0_protocols(self):
        assert hasattr(pycurl, 'PROTO_IMAP')
        assert hasattr(pycurl, 'PROTO_IMAPS')
        assert hasattr(pycurl, 'PROTO_POP3')
        assert hasattr(pycurl, 'PROTO_POP3S')
        assert hasattr(pycurl, 'PROTO_RTSP')
        assert hasattr(pycurl, 'PROTO_SMTP')
        assert hasattr(pycurl, 'PROTO_SMTPS')
    
    @util.min_libcurl(7, 21, 0)
    def test_7_21_0_protocols(self):
        assert hasattr(pycurl, 'PROTO_RTMP')
        assert hasattr(pycurl, 'PROTO_RTMPE')
        assert hasattr(pycurl, 'PROTO_RTMPS')
        assert hasattr(pycurl, 'PROTO_RTMPT')
        assert hasattr(pycurl, 'PROTO_RTMPTE')
        assert hasattr(pycurl, 'PROTO_RTMPTS')
    
    @util.min_libcurl(7, 21, 2)
    def test_7_21_2_protocols(self):
        assert hasattr(pycurl, 'PROTO_GOPHER')
