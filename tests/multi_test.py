#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et

import pycurl
import unittest

from . import app
from . import runwsgi
from . import util

setup_module_1, teardown_module_1 = runwsgi.app_runner_setup((app.app, 8380))
setup_module_2, teardown_module_2 = runwsgi.app_runner_setup((app.app, 8381))

def setup_module(mod):
    setup_module_1(mod)
    setup_module_2(mod)

def teardown_module(mod):
    teardown_module_2(mod)
    teardown_module_1(mod)

class MultiTest(unittest.TestCase):
    def test_multi(self):
        io1 = util.StringIO()
        io2 = util.StringIO()
        m = pycurl.CurlMulti()
        m.handles = []
        c1 = pycurl.Curl()
        c2 = pycurl.Curl()
        c1.setopt(c1.URL, 'http://localhost:8380/success')
        c1.setopt(c1.WRITEFUNCTION, io1.write)
        c2.setopt(c2.URL, 'http://localhost:8381/success')
        c2.setopt(c1.WRITEFUNCTION, io2.write)
        m.add_handle(c1)
        m.add_handle(c2)
        m.handles.append(c1)
        m.handles.append(c2)

        num_handles = len(m.handles)
        while num_handles:
            while 1:
                ret, num_handles = m.perform()
                if ret != pycurl.E_CALL_MULTI_PERFORM:
                    break
            m.select(1.0)

        m.remove_handle(c2)
        m.remove_handle(c1)
        del m.handles
        m.close()
        c1.close()
        c2.close()
        
        self.assertEqual('success', io1.getvalue())
        self.assertEqual('success', io2.getvalue())
