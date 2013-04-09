#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et

import pycurl
import unittest
import nose.tools

from . import util

class GlobalInitTest(unittest.TestCase):
    def test_global_init_default(self):
        # initialize libcurl with DEFAULT flags
        pycurl.global_init(pycurl.GLOBAL_DEFAULT)
        pycurl.global_cleanup()

    def test_global_init_ack_eintr(self):
        # the GLOBAL_ACK_EINTR flag was introduced in libcurl-7.30, but can also
        # be backported for older versions of libcurl at the distribution level
        if not util.pycurl_version_less_than(7, 30) or hasattr(pycurl, 'GLOBAL_ACK_EINTR'):
            # initialize libcurl with the GLOBAL_ACK_EINTR flag
            pycurl.global_init(pycurl.GLOBAL_ACK_EINTR)
            pycurl.global_cleanup()
    
    @nose.tools.raises(ValueError)
    def test_global_init_bogus(self):
        # initialize libcurl with bogus flags
        pycurl.global_init(0xffff)
