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

# Initialize pycurl
c = pycurl.Curl()
c.setopt(pycurl.URL, url)
c.setopt(pycurl.UPLOAD, 1)

# Two versions with the same semantics here, but the filereader version
# is useful when you have to process the data which is read before returning
if 1:
    c.setopt(pycurl.READFUNCTION, filereader(open(filename, 'rb')).read_callback)
else:
    c.setopt(pycurl.READFUNCTION, open(filename, 'rb').read)

# Set size of file to be uploaded, use LARGE option if file size is
# greater than 2GB
filesize = os.path.getsize(filename)
if filesize > 2**31:
    c.setopt(pycurl.INFILESIZE_LARGE, filesize)
else:
    c.setopt(pycurl.INFILESIZE, filesize)

# Start transfer
print 'Uploading file %s to url %s' % (filename, url)
c.perform()
c.close()
