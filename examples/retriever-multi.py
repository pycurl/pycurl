#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

import sys
assert sys.version[:3] >= "2.2", "requires Python 2.2 or better"
import pycurl
# We should ignore SIGPIPE when using pycurl.NOSIGNAL - see the libcurl
# documentation `libcurl-the-guide' for more info.
try:
    import signal
    from signal import SIGPIPE, SIG_IGN
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except ImportError:
    pass

# Get args
num_conn = 10
try:
    urls = open(sys.argv[1]).readlines()
    if len(sys.argv) >= 3:
        num_conn = int(sys.argv[2])
except:
    print "Usage: %s <file with URLs to fetch> [<# of concurrent connections>]" % sys.argv[0]
    raise SystemExit

# Make a queue with (url, filename) tuples
queue = []
fileno = 1
for url in urls:
    url = url.strip()
    if not url or url[0] == "#":
        continue
    filename = "data_%d" % (fileno)
    queue.append((url, filename))
    fileno += 1
del fileno, url, urls

# Check args
assert queue, "no URLs given"
num_urls = len(queue)
num_conn = min(num_conn, num_urls)
assert 1 <= num_conn <= 10000, "invalid number of connections"
print "----- Getting", num_urls, "URLs using", num_conn, "connections -----"

# Preallocate a list of curl objects
m = pycurl.CurlMulti()
m.handles = []
for i in range(num_conn):
    c = pycurl.Curl()
    c.fp = None
    c.setopt(pycurl.HTTPHEADER, ["User-Agent: PycURL"])
    c.setopt(pycurl.FOLLOWLOCATION, 1)
    c.setopt(pycurl.MAXREDIRS, 5)
    c.setopt(pycurl.CONNECTTIMEOUT, 30)
    c.setopt(pycurl.NOSIGNAL, 1)
    m.handles.append(c)

freelist = m.handles[:]
num_processed = 0
while num_processed < num_urls:
    # If there is an url to process and a free curl object, add to multi stack
    while queue and freelist:
        url, filename = queue.pop(0)
        c = freelist.pop()
        c.fp = open(filename, "wb")
        c.setopt(pycurl.URL, url)
        c.setopt(pycurl.WRITEDATA, c.fp)
        m.add_handle(c)
    # Run the internal curl state machine for the multi stack
    while 1:
        ret, num_handles = m.perform()
        if ret != pycurl.E_CALL_MULTI_PERFORM:
            break
    # Check for curl objects which have terminated, and add them to the freelist
    while 1:
        num_q, ok, err = m.info_read()
        for c in ok:
            c.fp.close()
            c.fp = None
            m.remove_handle(c)
            print "Success:", c
            freelist.append(c)
        for c, errno, errmsg in err:
            c.fp.close()
            c.fp = None
            m.remove_handle(c)
            print "Failed:", c, errno, errmsg
            freelist.append(c)
        num_processed += len(ok) + len(err)
        if num_q == 0:
            break
    # currently no more I/O is pending, could do something in the meantime
    # (display a progress bar, etc.)
    m.select()

# Cleanup
for c in m.handles:
    if c.fp is not None:
        c.fp.close()
    c.close()
m.close()

# Delete objects (just for testing the refcounts)
del c, m, freelist, queue

