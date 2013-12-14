#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et

import pycurl
import unittest
import sys

class PycurlObjectTest(unittest.TestCase):
    def setUp(self):
        self.curl = pycurl.Curl()
    
    def tearDown(self):
        self.curl.close()
    
    def test_set_attribute_curl(self):
        self.instantiate_and_check(self.check_set_attribute, 'Curl')
    
    def test_get_attribute_curl(self):
        self.instantiate_and_check(self.check_get_attribute, 'Curl')
    
    def test_delete_attribute_curl(self):
        self.instantiate_and_check(self.check_delete_attribute, 'Curl')
    
    def test_set_attribute_multi(self):
        self.instantiate_and_check(self.check_set_attribute, 'CurlMulti')
    
    def test_get_attribute_multi(self):
        self.instantiate_and_check(self.check_get_attribute, 'CurlMulti')
    
    def test_delete_attribute_multi(self):
        self.instantiate_and_check(self.check_delete_attribute, 'CurlMulti')
    
    def test_set_attribute_share(self):
        self.instantiate_and_check(self.check_set_attribute, 'CurlShare')
    
    def test_get_attribute_share(self):
        self.instantiate_and_check(self.check_get_attribute, 'CurlShare')
    
    def test_delete_attribute_share(self):
        self.instantiate_and_check(self.check_delete_attribute, 'CurlShare')
    
    def instantiate_and_check(self, fn, cls_name):
        cls = getattr(pycurl, cls_name)
        instance = cls()
        try:
            fn(instance)
        finally:
            instance.close()
    
    def check_set_attribute(self, pycurl_obj):
        assert not hasattr(pycurl_obj, 'attr')
        pycurl_obj.attr = 1
        assert hasattr(pycurl_obj, 'attr')
    
    def check_get_attribute(self, pycurl_obj):
        assert not hasattr(pycurl_obj, 'attr')
        pycurl_obj.attr = 1
        self.assertEqual(1, pycurl_obj.attr)
    
    def check_delete_attribute(self, pycurl_obj):
        assert not hasattr(pycurl_obj, 'attr')
        pycurl_obj.attr = 1
        self.assertEqual(1, pycurl_obj.attr)
        assert hasattr(pycurl_obj, 'attr')
        del pycurl_obj.attr
        assert not hasattr(pycurl_obj, 'attr')
