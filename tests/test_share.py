#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

import sys
import pycurl
import threading

print >>sys.stderr, 'Testing', pycurl.version


class Test(threading.Thread):

    def __init__(self, share):
        threading.Thread.__init__(self)
        self.curl = pycurl.Curl()
        self.curl.setopt(pycurl.URL, 'http://curl.haxx.se')
        self.curl.setopt(pycurl.SHARE, share)

    def run(self):
        self.curl.perform()
        self.curl.close()

s = pycurl.CurlShare()
s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_COOKIE)
s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_DNS)

t1 = Test(s)
t2 = Test(s)

t1.start()
t2.start()
del s
