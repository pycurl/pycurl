#! /usr/bin/env python
# -*- coding: utf-8 -*-
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
    
    def test_get_missing_attribute_curl(self):
        self.instantiate_and_check(self.check_get_missing_attribute, 'Curl')
    
    def test_delete_attribute_curl(self):
        self.instantiate_and_check(self.check_delete_attribute, 'Curl')
    
    def test_delete_missing_attribute_curl(self):
        self.instantiate_and_check(self.check_delete_missing_attribute, 'Curl')
    
    def test_set_attribute_multi(self):
        self.instantiate_and_check(self.check_set_attribute, 'CurlMulti')
    
    def test_get_attribute_multi(self):
        self.instantiate_and_check(self.check_get_attribute, 'CurlMulti')
    
    def test_get_missing_attribute_curl(self):
        self.instantiate_and_check(self.check_get_missing_attribute, 'CurlMulti')
    
    def test_delete_attribute_multi(self):
        self.instantiate_and_check(self.check_delete_attribute, 'CurlMulti')
    
    def test_delete_missing_attribute_curl(self):
        self.instantiate_and_check(self.check_delete_missing_attribute, 'CurlMulti')
    
    def test_set_attribute_share(self):
        self.instantiate_and_check(self.check_set_attribute, 'CurlShare')
    
    def test_get_attribute_share(self):
        self.instantiate_and_check(self.check_get_attribute, 'CurlShare')
    
    def test_get_missing_attribute_curl(self):
        self.instantiate_and_check(self.check_get_missing_attribute, 'CurlShare')
    
    def test_delete_attribute_share(self):
        self.instantiate_and_check(self.check_delete_attribute, 'CurlShare')
    
    def test_delete_missing_attribute_curl(self):
        self.instantiate_and_check(self.check_delete_missing_attribute, 'CurlShare')
    
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
    
    def check_get_missing_attribute(self, pycurl_obj):
        try:
            getattr(pycurl_obj, 'doesnotexist')
            self.fail('Expected an AttributeError exception to be raised')
        except AttributeError:
            pass
    
    def check_delete_attribute(self, pycurl_obj):
        assert not hasattr(pycurl_obj, 'attr')
        pycurl_obj.attr = 1
        self.assertEqual(1, pycurl_obj.attr)
        assert hasattr(pycurl_obj, 'attr')
        del pycurl_obj.attr
        assert not hasattr(pycurl_obj, 'attr')
    
    def check_delete_missing_attribute(self, pycurl_obj):
        try:
            del pycurl_obj.doesnotexist
            self.fail('Expected an AttributeError exception to be raised')
        except AttributeError:
            pass
    
    def test_modify_attribute_curl(self):
        self.check_modify_attribute(pycurl.Curl, 'READFUNC_PAUSE')
    
    def test_modify_attribute_multi(self):
        self.check_modify_attribute(pycurl.CurlMulti, 'E_MULTI_OK')
    
    def test_modify_attribute_share(self):
        self.check_modify_attribute(pycurl.CurlShare, 'SH_SHARE')
    
    def check_modify_attribute(self, cls, name):
        obj1 = cls()
        obj2 = cls()
        old_value = getattr(obj1, name)
        self.assertNotEqual('helloworld', old_value)
        # value should be identical to pycurl global
        self.assertEqual(old_value, getattr(pycurl, name))
        setattr(obj1, name, 'helloworld')
        self.assertEqual('helloworld', getattr(obj1, name))
        
        # change does not affect other existing objects
        self.assertEqual(old_value, getattr(obj2, name))
        
        # change does not affect objects created later
        obj3 = cls()
        self.assertEqual(old_value, getattr(obj3, name))
