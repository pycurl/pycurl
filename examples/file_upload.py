#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

import pycurl
import sys
import os.path

# Class which holds a file reference and the read callback
class filereader:

    def __init__(self, f):
        self.f = f

    def read_callback(self, size):
        return self.f.read(size)


# Use filereader class to hold the file reference and callback
def version_1(filename, url):
    reader = filereader(open(filename, 'rb'))
    filesize = os.path.getsize(filename)
    c = pycurl.Curl()
    c.setopt(pycurl.URL, url)
    c.setopt(pycurl.READFUNCTION, reader.read_callback)
    c.setopt(pycurl.INFILESIZE_LARGE, filesize) # to handle > 2GB file sizes
    c.setopt(pycurl.UPLOAD, 1)
    return c

# Use the builtin file read method as the callback
def version_2(filename, url):
    filesize = os.path.getsize(filename)
    c = pycurl.Curl()
    c.setopt(pycurl.URL, url)
    c.setopt(pycurl.READFUNCTION, open(filename, 'rb').read)
    c.setopt(pycurl.INFILESIZE_LARGE, filesize) # to handle > 2GB file sizes
    c.setopt(pycurl.UPLOAD, 1)
    return c

# Check commandline arguments
if len(sys.argv) < 3:
    print "Usage: %s <url> <file to upload>" % sys.argv[0]
    raise SystemExit
else:
    url = sys.argv[1]
    filename = sys.argv[2]

if not os.path.exists(filename):
    print "Error: the file '%s' does not exist" % filename
    raise SystemExit

# They both do the same, version 2 is fine if you don't need to process the
# data read from the callback before returning
c = version_1(filename, url)
# Start transfer
print 'Uploading file %s to url %s' % (filename, url)
c.perform()
c.close()
