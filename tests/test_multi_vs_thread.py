#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

import os, sys, time
from threading import Thread, RLock
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import pycurl

# We should ignore SIGPIPE when using pycurl.NOSIGNAL - see
# the libcurl tutorial for more info.
try:
    import signal
    from signal import SIGPIPE, SIG_IGN
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except ImportError:
    pass

# The conclusion is: the multi interface is fastest!

NUM_PAGES = 30
NUM_THREADS = 10
assert NUM_PAGES % NUM_THREADS == 0

##URL = "http://pycurl.sourceforge.net/tests/testgetvars.php?%d"
URL = "http://pycurl.sourceforge.net/tests/teststaticpage.html?%d"


#
# util
#

class Curl:
    def __init__(self, url):
        self.url = url
        self.body = StringIO()
        self.http_code = -1
        # pycurl API calls
        self._curl = pycurl.Curl()
        self._curl.setopt(pycurl.URL, self.url)
        self._curl.setopt(pycurl.WRITEFUNCTION, self.body.write)
        self._curl.setopt(pycurl.NOSIGNAL, 1)

    def perform(self):
        self._curl.perform()

    def close(self):
        self.http_code = self._curl.getinfo(pycurl.HTTP_CODE)
        self._curl.close()


def print_result(items):
    return  # DO NOTHING
    #
    for c in items:
        data = c.body.getvalue()
        if 0:
            print "**********", c.url, "**********"
            print data
        elif 1:
            print "%-60s   %3d   %6d" % (c.url, c.http_code, len(data))


###
### 1) multi
###

def test_multi():
    clock1 = time.time()

    # init
    handles = []
    m = pycurl.CurlMulti()
    for i in range(NUM_PAGES):
        c = Curl(URL %i)
        m.add_handle(c._curl)
        handles.append(c)

    clock2 = time.time()

    # stir state machine into action
    while 1:
        ret, num_handles = m.perform()
        if ret != pycurl.E_CALL_MULTI_PERFORM:
            break

    # get data
    while num_handles:
        m.select(1.0)
        while 1:
            ret, num_handles = m.perform()
            if ret != pycurl.E_CALL_MULTI_PERFORM:
                break

    clock3 = time.time()

    # close handles
    for c in handles:
        c.close()
    m.close()

    clock4 = time.time()
    print "multi  interface:        %d pages: perform %5.2f secs, total %5.2f secs" % (NUM_PAGES, clock3 - clock2, clock4 - clock1)

    # print result
    print_result(handles)



###
### 2) thread
###

class Test(Thread):
    def __init__(self, lock=None):
        Thread.__init__(self)
        self.lock = lock
        self.items = []

    def run(self):
        if self.lock:
            self.lock.acquire()
            self.lock.release()
        for c in self.items:
            c.perform()


def test_threads(lock=None):
    clock1 = time.time()

    # create and start threads, but block them
    if lock:
        lock.acquire()

    # init (FIXME - this is ugly)
    threads = []
    handles = []
    t = None
    for i in range(NUM_PAGES):
        if i % (NUM_PAGES / NUM_THREADS) == 0:
            t = Test(lock)
            if lock:
                t.start()
            threads.append(t)
        c = Curl(URL % i)
        t.items.append(c)
        handles.append(c)
    assert len(handles) == NUM_PAGES
    assert len(threads) == NUM_THREADS

    clock2 = time.time()

    #
    if lock:
        # release lock to let the blocked threads run
        lock.release()
    else:
        # start threads
        for t in threads:
            t.start()
    # wait for threads to finish
    for t in threads:
        t.join()

    clock3 = time.time()

    # close handles
    for c in handles:
        c.close()

    clock4 = time.time()
    if lock:
        print "thread interface [lock]: %d pages: perform %5.2f secs, total %5.2f secs" % (NUM_PAGES, clock3 - clock2, clock4 - clock1)
    else:
        print "thread interface:        %d pages: perform %5.2f secs, total %5.2f secs" % (NUM_PAGES, clock3 - clock2, clock4 - clock1)

    # print result
    print_result(handles)



###
### 3) thread - threads grab curl objects on demand from a shared pool
###

class TestPool(Thread):
    def __init__(self, lock, pool):
        Thread.__init__(self)
        self.lock = lock
        self.pool = pool

    def run(self):
        while 1:
            self.lock.acquire()
            c = None
            if self.pool:
                c = self.pool.pop()
            self.lock.release()
            if c is None:
                break
            c.perform()


def test_thread_pool(lock):
    clock1 = time.time()

    # init
    handles = []
    for i in range(NUM_PAGES):
        c = Curl(URL %i)
        handles.append(c)

    # create and start threads, but block them
    lock.acquire()
    threads = []
    pool = handles[:]   # shallow copy of the list, shared for pop()
    for i in range(NUM_THREADS):
        t = TestPool(lock, pool)
        t.start()
        threads.append(t)
    assert len(pool) == NUM_PAGES
    assert len(threads) == NUM_THREADS

    clock2 = time.time()

    # release lock to let the blocked threads run
    lock.release()

    # wait for threads to finish
    for t in threads:
        t.join()

    clock3 = time.time()

    # close handles
    for c in handles:
        c.close()

    clock4 = time.time()
    print "thread interface [pool]: %d pages: perform %5.2f secs, total %5.2f secs" % (NUM_PAGES, clock3 - clock2, clock4 - clock1)

    # print result
    print_result(handles)



lock = RLock()
if 1:
    test_multi()
    test_threads()
    test_threads(lock)
    test_thread_pool(lock)
else:
    test_thread_pool(lock)
    test_threads(lock)
    test_threads()
    test_multi()

