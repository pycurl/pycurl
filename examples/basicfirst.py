#! /usr/bin/env python
# vi:ts=4:et
import pycurl


class Test:
    def __init__(self):
        self.contents = b''

    def body_callback(self, buf):
        self.contents = self.contents + buf


import sys
sys.stderr.write("Testing %s\n" % pycurl.version)

t = Test()
c = pycurl.Curl()
c.setopt(c.URL, 'https://curl.haxx.se/dev/')
c.setopt(c.WRITEFUNCTION, t.body_callback)
c.perform()
c.close()

print(t.contents)
