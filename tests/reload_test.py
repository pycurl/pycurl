#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import pytest
import unittest

class ReloadTest(unittest.TestCase):
    @pytest.mark.standalone
    def test_reloading(self):
        try:
            # python 2
            reload_fn = reload
        except NameError:
            # python 3
            import imp
            reload_fn = imp.reload
        reload_fn(pycurl)
