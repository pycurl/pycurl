#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

import os, sys
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import pycurl


urls = (
    "http://curl.haxx.se",
    "http://www.python.org",
    "http://pycurl.sourceforge.net",
)

# Read list of URIs from file specified on commandline
try:
    urls = open(sys.argv[1], "rb").readlines()
except IndexError:
    # No file was specified
    pass

# timer callback
def timer(msecs):
    print 'Timer callback msecs:', msecs

# socket callback
def socket(event, socket, multi, data):
    print event, socket, multi, data
#    multi.assign(socket, timer)

# init
m = pycurl.CurlMulti()
m.setopt(pycurl.M_PIPELINING, 1)
m.setopt(pycurl.M_TIMERFUNCTION, timer)
m.setopt(pycurl.M_SOCKETFUNCTION, socket)
m.handles = []
for url in urls:
    c = pycurl.Curl()
    # save info in standard Python attributes
    c.url = url
    c.body = StringIO()
    c.http_code = -1
    m.handles.append(c)
    # pycurl API calls
    c.setopt(c.URL, c.url)
    c.setopt(c.WRITEFUNCTION, c.body.write)
    m.add_handle(c)

# get data
num_handles = len(m.handles)
while num_handles:
     while 1:
         ret, num_handles = m.socket_all()
         if ret != pycurl.E_CALL_MULTI_PERFORM:
             break
     # currently no more I/O is pending, could do something in the meantime
     # (display a progress bar, etc.)
     m.select(1.0)

# close handles
for c in m.handles:
    # save info in standard Python attributes
    c.http_code = c.getinfo(c.HTTP_CODE)
    # pycurl API calls
    m.remove_handle(c)
    c.close()
m.close()

# print result
for c in m.handles:
    data = c.body.getvalue()
    if 0:
        print "**********", c.url, "**********"
        print data
    else:
        print "%-53s http_code %3d, %6d bytes" % (c.url, c.http_code, len(data))

