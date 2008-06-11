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
import select

sockets = set()
timeout = 0

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
    global timeout
    timeout = msecs
    print 'Timer callback msecs:', msecs

# socket callback
def socket(event, socket, multi, data):
    if event == pycurl.POLL_REMOVE:
        print "Remove Socket %d"%socket
        sockets.remove(socket)
    else:
        if socket not in sockets:
            print "Add socket %d"%socket
            sockets.add(socket)
    print event, socket, multi, data

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

while (pycurl.E_CALL_MULTI_PERFORM==m.socket_all()[0]):
    pass
    
timeout = m.timeout()


while True:
    (rr, wr, er) = select.select(sockets,sockets,sockets,timeout/1000.0)
    socketSet = set(rr+wr+er)
    if socketSet:
        for s in socketSet:
            while True:
                (ret,running) = m.socket_action(s,0)
                if ret!=pycurl.E_CALL_MULTI_PERFORM:
                    break
    else:
        (ret,running) = m.socket_action(pycurl.SOCKET_TIMEOUT,0)
    if running==0:
        break

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

