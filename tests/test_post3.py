#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

import urllib
POSTSTRING = urllib.urlencode({'field1':'value1', 'field2':'value2 with blanks', 'field3':'value3'})

class test:

    def __init__(self):
        self.finished = False

    def read_cb(self, size):
        assert len(POSTSTRING) <= size
        if not self.finished:
            self.finished = True
            return POSTSTRING
        else:
            # Nothing more to read
            return ""

import pycurl
c = pycurl.Curl()
t = test()
c.setopt(c.URL, 'http://pycurl.sourceforge.net/tests/testpostvars.php')
c.setopt(c.POST, 1)
c.setopt(c.POSTFIELDSIZE, len(POSTSTRING))
c.setopt(c.READFUNCTION, t.read_cb)
c.setopt(c.VERBOSE, 1)
c.perform()
c.close()
