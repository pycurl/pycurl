# $Id$

import sys
import pycurl
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

url = 'http://curl.haxx.se/dev/'

print 'Testing curl version', pycurl.version

body = StringIO()
c = pycurl.init()
c.setopt(pycurl.URL, url)
c.setopt(pycurl.WRITEFUNCTION, body.write)
c.perform()
c.cleanup()

contents = body.getvalue()
print contents
