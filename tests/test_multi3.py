# $Id$
# vi:ts=4:et

# same as test_multi2.py, but enforce some debugging and strange API-calls

import os, sys, time
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import pycurl


urls = (
    "http://curl.haxx.se",
    "http://www.python.org",
    "http://pycurl.sourceforge.net",
    "http://pycurl.sourceforge.net/THIS_HANDLE_IS_CLOSED",
)

# init
m = pycurl.CurlMulti()
m.handles = []
for url in urls:
    c = pycurl.Curl()
    # save info in standard Python attributes
    c.url = url
    c.body = StringIO()
    c.http_code = -1
    c.debug = 0
    m.handles.append(c)
    # pycurl API calls
    c.setopt(c.URL, c.url)
    c.setopt(c.WRITEFUNCTION, c.body.write)
    m.add_handle(c)

# debug - close a handle
if 1:
    c = m.handles[3]
    c.debug = 1
    c.close()

# get data
while 1:
    num_handles = m.perform()
    if num_handles == 0:
        break
    # currently no more I/O is pending, could do something in the meantime
    # (display a progress bar, etc.)
    time.sleep(0.01)

# close handles
for c in m.handles:
    # save info in standard Python attributes
    try:
        c.http_code = c.getinfo(c.HTTP_CODE)
    except pycurl.error:
        # handle already closed - see debug above
        assert c.debug
        c.http_code = -1
    # pycurl API calls
    if 0:
        m.remove_handle(c)
        c.close()
    elif 0:
        # in the C API this is the wrong calling order, but pycurl
        # handles this automatically
        c.close()
        m.remove_handle(c)
    else:
        # actually, remove_handle is called automatically on close
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

