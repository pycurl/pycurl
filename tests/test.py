#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

import sys, threading, time
import pycurl

# We should ignore SIGPIPE when using pycurl.NOSIGNAL - see
# the libcurl tutorial for more info.
try:
    import signal
    from signal import SIGPIPE, SIG_IGN
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except ImportError:
    pass


class Test(threading.Thread):
    def __init__(self, url, ofile):
        threading.Thread.__init__(self)
        self.curl = pycurl.Curl()
        self.curl.setopt(pycurl.URL, url)
        self.curl.setopt(pycurl.WRITEDATA, ofile)
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.MAXREDIRS, 5)
        self.curl.setopt(pycurl.NOSIGNAL, 1)

    def run(self):
        self.curl.perform()
        self.curl.close()
        sys.stdout.write(".")
        sys.stdout.flush()


# Read list of URIs from file specified on commandline
try:
    urls = open(sys.argv[1]).readlines()
except IndexError:
    # No file was specified, show usage string
    print "Usage: %s <file with uris to fetch>" % sys.argv[0]
    raise SystemExit

# Initialize thread array and the file number
threads = []
fileno = 0

# Start one thread per URI in parallel
t1 = time.time()
for url in urls:
    f = open(str(fileno), "wb")
    t = Test(url.rstrip(), f)
    t.start()
    threads.append((t, f))
    fileno = fileno + 1
# Wait for all threads to finish
for thread, file in threads:
    thread.join()
    file.close()
t2 = time.time()
print "\n** Multithreading, %d seconds elapsed for %d uris" % (int(t2-t1), len(urls))

# Start one thread per URI in sequence
fileno = 0
t1 = time.time()
for url in urls:
    f = open(str(fileno), "wb")
    t = Test(url.rstrip(), f)
    t.start()
    fileno = fileno + 1
    t.join()
    f.close()
t2 = time.time()
print "\n** Singlethreading, %d seconds elapsed for %d uris" % (int(t2-t1), len(urls))
