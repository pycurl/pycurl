# $Id$

import sys
import pycurl

url = 'http://curl.haxx.se/dev/'
contents = ''

def body_callback(buf):
    global contents
    contents = contents + buf
    return len(buf)

print 'Testing', pycurl.version

c = pycurl.Curl()
c.setopt(c.URL, url)
c.setopt(c.WRITEFUNCTION, body_callback)
c.setopt(c.HTTPHEADER, ["I-am-a-silly-programmer: yes indeed you are",
                        "User-Agent: Python interface for libcURL"])
c.perform()
c.close()

print contents
