#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et

import pycurl
import unittest
import gc

debug = False

class MemoryMgmtTest(unittest.TestCase):
    def maybe_enable_debug(self):
        if debug:
            flags = gc.DEBUG_COLLECTABLE | gc.DEBUG_UNCOLLECTABLE
            # python 3 has no DEBUG_OBJECTS
            if hasattr(gc, 'DEBUG_OBJECTS'):
                flags |= gc.DEBUG_OBJECTS
                flags |= gc.DEBUG_STATS
            gc.set_debug(flags)
            gc.collect()

            print("Tracked objects:", len(gc.get_objects()))
    
    def maybe_print_objects(self):
        if debug:
            print("Tracked objects:", len(gc.get_objects()))
    
    def tearDown(self):
        gc.set_debug(0)
    
    def test_multi_collection(self):
        gc.collect()
        self.maybe_enable_debug()

        multi = pycurl.CurlMulti()
        t = []
        searches = []
        for a in range(100):
            curl = pycurl.Curl()
            multi.add_handle(curl)
            t.append(curl)
            
            c_id = id(curl)
            searches.append(c_id)
        m_id = id(multi)
        searches.append(m_id)

        self.maybe_print_objects()

        for curl in t:
            curl.close()
            multi.remove_handle(curl)

        self.maybe_print_objects()

        del curl
        del t
        del multi

        self.maybe_print_objects()
        gc.collect()
        self.maybe_print_objects()
        
        objects = gc.get_objects()
        for search in searches:
            for object in objects:
                assert search != id(object)
    
    def test_multi_cycle(self):
        gc.collect()
        self.maybe_enable_debug()

        multi = pycurl.CurlMulti()
        t = []
        searches = []
        for a in range(100):
            curl = pycurl.Curl()
            multi.add_handle(curl)
            t.append(curl)
            
            c_id = id(curl)
            searches.append(c_id)
        m_id = id(multi)
        searches.append(m_id)

        self.maybe_print_objects()

        del curl
        del t
        del multi

        self.maybe_print_objects()
        gc.collect()
        self.maybe_print_objects()
        
        objects = gc.get_objects()
        for search in searches:
            for object in objects:
                assert search != id(object)
    
    def test_share_collection(self):
        gc.collect()
        self.maybe_enable_debug()

        share = pycurl.CurlShare()
        t = []
        searches = []
        for a in range(100):
            curl = pycurl.Curl()
            curl.setopt(curl.SHARE, share)
            t.append(curl)
            
            c_id = id(curl)
            searches.append(c_id)
        m_id = id(share)
        searches.append(m_id)

        self.maybe_print_objects()

        for curl in t:
            curl.unsetopt(curl.SHARE)
            curl.close()

        self.maybe_print_objects()

        del curl
        del t
        del share

        self.maybe_print_objects()
        gc.collect()
        self.maybe_print_objects()
        
        objects = gc.get_objects()
        for search in searches:
            for object in objects:
                assert search != id(object)
    
    def test_share_cycle(self):
        gc.collect()
        self.maybe_enable_debug()

        share = pycurl.CurlShare()
        t = []
        searches = []
        for a in range(100):
            curl = pycurl.Curl()
            curl.setopt(curl.SHARE, share)
            t.append(curl)
            
            c_id = id(curl)
            searches.append(c_id)
        m_id = id(share)
        searches.append(m_id)

        self.maybe_print_objects()

        del curl
        del t
        del share

        self.maybe_print_objects()
        gc.collect()
        self.maybe_print_objects()
        
        objects = gc.get_objects()
        for search in searches:
            for object in objects:
                assert search != id(object)
