#! /usr/bin/env python
# vi:ts=4:et

import importlib
import pycurl
import pytest
import unittest

class ReloadTest(unittest.TestCase):
    @pytest.mark.standalone
    def test_reloading(self):
        importlib.reload(pycurl)
