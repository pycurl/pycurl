#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

import sys
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import pycurl

url = "http://curl.haxx.se/dev/"

print "Testing", pycurl.version

body = StringIO()
c = pycurl.Curl()
c.setopt(c.URL, url)
c.setopt(c.WRITEFUNCTION, body.write)
c.perform()
c.close()

contents = body.getvalue()
print contents
