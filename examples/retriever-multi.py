#! /usr/bin/env python
# vi:ts=4:et
# $Id$

import sys
import pycurl

try:
    urls = open(sys.argv[1]).readlines()
    num_conn = int(sys.argv[2])
except:
    print "Usage: %s <file with URLs to fetch> <# of concurrent connections>" % sys.argv[0]
    raise SystemExit

fileno = 0
queue = []
for u in urls:
    queue.append((u, 'data_%d' % fileno))
    fileno += 1

freelist = []
for c in range(num_conn):
    curl = pycurl.Curl()
    curl.setopt(pycurl.HTTPHEADER, ["User-Agent: PycURL"])
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    freelist.append(curl)

processed = 0
curls = {}
multi = pycurl.CurlMulti()

while processed < len(urls):
    while len(freelist) > 0:
        if len(queue) > 0:
            u, n = queue.pop(0)
            c = freelist.pop(0)
            f = open(n, "wb")
            c.setopt(pycurl.URL, u)
            c.setopt(pycurl.WRITEDATA, f)
            curls[c] = f
            multi.add_handle(c)
        else:
            break
    while 1:
        ret, num_handles = multi.perform()
        if ret != pycurl.E_CALL_MULTI_PERFORM:
            break
    while 1:
        num_q, handles = multi.info_read(num_conn)
        for h in handles:
            curls[h].close()
            freelist.append(h)
            multi.remove_handle(h)
        processed += len(handles)
        del handles
        if num_q == 0:
            break

for c in curls:
    c.close()
    multi.remove_handle(c)
    freelist.remove(c)

del curls
del freelist
