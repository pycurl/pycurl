# $Id$

import pycurl

def test(**args):
    print args

c = pycurl.init()
c.setopt(pycurl.URL, 'http://curl.haxx.se/')
c.setopt(pycurl.VERBOSE, 1)
c.setopt(pycurl.DEBUGFUNCTION, test)
c.perform()
c.cleanup()
