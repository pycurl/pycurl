#! /usr/bin/env python
# vi:ts=4:et
# $Id$

import sys
import pycurl


try:
    urls = open(sys.argv[1]).readlines()
    num_conn = int(sys.argv[2])
except:
    print "Usage: %s <file with URLs to fetch> <concurrency>" % sys.argv[0]
    raise SystemExit

fileno = 0
conn = 0
queue = []
curls = {}
multi = pycurl.CurlMulti()

for u in urls:
    queue.append((u, 'data_%d' % fileno))
    fileno += 1

while len(queue) > 0 or conn > 0:
    while conn < num_conn:
        if len(queue) > 0:
            u, n = queue.pop(0)
            f = open(n, "wb")
            curl = pycurl.Curl()
            curl.setopt(pycurl.URL, u)
            curl.setopt(pycurl.WRITEDATA, f)
            curl.setopt(pycurl.HTTPHEADER, ["User-Agent: PycURL"])
            curl.setopt(pycurl.FOLLOWLOCATION, 1)
            curl.setopt(pycurl.MAXREDIRS, 5)
            curl.setopt(pycurl.CONNECTTIMEOUT, 30)
            multi.add_handle(curl)
            curls[curl] = f
            conn += 1
        else:
            break
    while 1:
        ret, num_handles = multi.perform()
        if ret != pycurl.E_CALL_MULTI_PERFORM:
            break
    while 1:
        num_q, handles = multi.info_read(num_conn)
        for h in handles:
            h.close()
            multi.remove_handle(h)
            curls[h].close()
            del curls[h]
        conn -= len(handles)
        if num_q == 0:
            break

assert len(curls) == 0
multi.close()
