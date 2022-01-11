#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

try:
    import unittest2 as unittest
except ImportError:
    import unittest
import pycurl

CLASSES = (pycurl.Curl, pycurl.CurlMulti, pycurl.CurlShare)

class SubclassTest(unittest.TestCase):
    def test_baseclass_init(self):
        # base classes do not accept any arguments on initialization
        for baseclass in CLASSES:
            try:
                baseclass(0)
            except TypeError:
                pass
            else:
                raise AssertionError('Base class accepted invalid args')
            try:
                baseclass(a=1)
            except TypeError:
                pass
            else:
                raise AssertionError('Base class accepted invalid kwargs')

    def test_subclass_create(self):
        for baseclass in CLASSES:
            # test creation of a subclass
            class MyCurlClass(baseclass):
                pass
            # test creation of its object
            obj = MyCurlClass()
            # must be of type subclass, but also an instance of base class
            assert type(obj) == MyCurlClass
            assert isinstance(obj, baseclass)

    def test_subclass_init(self):
        for baseclass in CLASSES:
            class MyCurlClass(baseclass):
                def __init__(self, x, y=4):
                    self.x = x
                    self.y = y
            # subclass __init__ must be able to accept args and kwargs
            obj = MyCurlClass(3)
            assert obj.x == 3
            assert obj.y == 4
            obj = MyCurlClass(5, y=6)
            assert obj.x == 5
            assert obj.y == 6
            # and it must throw TypeError if arguments don't match
            try:
                MyCurlClass(1, 2, 3, kwarg=4)
            except TypeError:
                pass
            else:
                raise AssertionError('Subclass accepted invalid arguments')

    def test_subclass_method(self):
        for baseclass in CLASSES:
            class MyCurlClass(baseclass):
                def my_method(self, x):
                    return x + 1
            obj = MyCurlClass()
            # methods must be able to accept arguments and return a value
            assert obj.my_method(1) == 2

    def test_subclass_method_override(self):
        # setopt args for each base class
        args = {
            pycurl.Curl:      (pycurl.VERBOSE, 1),
            pycurl.CurlMulti: (pycurl.M_MAXCONNECTS, 3),
            pycurl.CurlShare: (pycurl.SH_SHARE, pycurl.LOCK_DATA_COOKIE),
        }
        for baseclass in CLASSES:
            class MyCurlClass(baseclass):
                def setopt(self, option, value):
                    # base method must not be overwritten
                    assert super().setopt != self.setopt
                    # base method mut be callable, setopt must return None
                    assert super().setopt(option, value) is None
                    # return something else
                    return 'my setopt'
            obj = MyCurlClass()
            assert obj.setopt(*args[baseclass]) == 'my setopt'
