#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

import sys
import pycurl
try:
    import signal
    from signal import SIGPIPE, SIG_IGN
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except ImportError:
    pass

assert sys.version[:3] >= "2.2", "requires Python 2.2 or better"

try:
    urls = open(sys.argv[1]).readlines()
    num_conn = int(sys.argv[2])
except:
    print "Usage: %s <file with URLs to fetch> <# of concurrent connections>" % sys.argv[0]
    raise SystemExit

num_conn = min(num_conn, len(urls))
assert 1 <= num_conn <= 10000, "invalid number of connections"

# Make a queue with (url, filename) tuples
fileno = 0
queue = []
for u in urls:
    queue.append((u, "data_%d" % fileno))
    fileno += 1

# Preallocate a list of curl objects 
freelist = []
for c in range(num_conn):
    curl = pycurl.Curl()
    curl.setopt(pycurl.HTTPHEADER, ["User-Agent: PycURL"])
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    curl.setopt(pycurl.NOSIGNAL, 1)
    freelist.append(curl)

processed = 0
multi = pycurl.CurlMulti()

while processed < len(urls):
    # If there is an url to process and a free curl object, add to multi stack
    while queue and freelist:
        u, n = queue.pop(0)
        c = freelist.pop(0)
        c.f = open(n, "wb")
        c.setopt(pycurl.URL, u)
        c.setopt(pycurl.WRITEDATA, c.f)
        multi.add_handle(c)
    # Run the internal curl state machine for the multi stack
    while 1:
        ret, num_handles = multi.perform()
        if ret != pycurl.E_CALL_MULTI_PERFORM:
            break
    # Check for curl objects which have terminated, and add them to the freelist
    while 1:
        num_q, handles = multi.info_read(num_conn)
        for h in handles:
            h.f.close()
            multi.remove_handle(h)
            freelist.append(h)
        processed += len(handles)
        if num_q == 0:
            break

# Cleanup
for c in freelist:
    c.close()
    multi.remove_handle(c)
del c
multi.close()
del freelist, queue, multi
