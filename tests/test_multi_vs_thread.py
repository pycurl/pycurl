# $Id$
# vi:ts=4:et

import os, sys, time
from threading import Thread
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import pycurl


#
# FIXME FIXME FIXME - this is a very first version and
#     needs much cleanup and comments
#
# anyway, the conclusion is: threads are much faster!
#

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
        # save info in standard Python attributes
        self.url = URL % i
        self.body = StringIO()
        self.http_code = -1
        # pycurl API calls
        self._curl = pycurl.init()
        self._curl.setopt(pycurl.URL, self.url)
        self._curl.setopt(pycurl.WRITEFUNCTION, self.body.write)

    def perform(self):
        self._curl.perform()

    def close(self):
        self.http_code = self._curl.getinfo(pycurl.HTTP_CODE)
        self._curl.cleanup()


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

clock1 = time.time()

# init
handles = []
m = pycurl.multi_init()
for i in range(NUM_PAGES):
    c = Curl(URL %i)
    m.add_handle(c._curl)
    handles.append(c)

clock2 = time.time()

# get data
while 1:
    num_handles = m.perform()
    if num_handles == 0:
        break
    # currently no more I/O is pending, could do something in the meantime
    # (display a progress bar, etc.)
    time.sleep(0.01)

clock3 = time.time()

# close handles
for c in handles:
    c.close()
m.cleanup()
del m

clock4 = time.time()
print "multi  interface: %d pages: perform %5.2f secs, total %5.2f secs" % (NUM_PAGES, clock3 - clock2, clock4 - clock1)

# print result
print_result(handles)

del handles



###
### 2) thread
###

class Test(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.items = []

    def run(self):
        for c in self.items:
            c.perform()


clock1 = time.time()

# init (FIXME - this is ugly)
handles = []
threads = []
t = None
for i in range(NUM_PAGES):
    if i % (NUM_PAGES / NUM_THREADS) == 0:
        t = Test()
        threads.append(t)
    c = Curl(URL % i)
    t.items.append(c)
    handles.append(c)
assert len(handles) == NUM_PAGES
assert len(threads) == NUM_THREADS
del t, c

clock2 = time.time()

# get data
for t in threads:
    t.start()
for t in threads:
    t.join()

clock3 = time.time()
del t, threads

# close handles
for c in handles:
    c.close()

clock4 = time.time()
print "thread interface: %d pages: perform %5.2f secs, total %5.2f secs" % (NUM_PAGES, clock3 - clock2, clock4 - clock1)

# print result
print_result(handles)

del handles


