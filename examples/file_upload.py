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

    def close(self):
        self.f.close()

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

# Configure pycurl
reader = filereader(open(filename, 'rb'))
filesize = os.path.getsize(filename)
c = pycurl.Curl()
c.setopt(pycurl.URL, url)
c.setopt(pycurl.READFUNCTION, reader.read_callback)
c.setopt(pycurl.INFILESIZE_LARGE, filesize) # to handle > 2GB file sizes
c.setopt(pycurl.UPLOAD, 1)

# Start transfer
print 'Posting file %s to url %s' % (filename, url)
c.perform()
c.close()
reader.close()
