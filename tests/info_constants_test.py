#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import unittest

from . import util

class InfoConstantsTest(unittest.TestCase):
    # CURLINFO_CONDITION_UNMET  was introduced in libcurl-7.19.4
    @util.min_libcurl(7, 19, 4)
    def test_condition_unmet(self):
        curl = pycurl.Curl()
        assert hasattr(curl, 'CONDITION_UNMET')
        curl.close()
