# $Id$

import pycurl
m = pycurl.multi_init()
c1 = pycurl.init()
c2 = pycurl.init()
c1.setopt(pycurl.URL, 'http://curl.haxx.se')
c2.setopt(pycurl.URL, 'http://python.org')
m.add_handle(c1)
m.add_handle(c2)
while 1:
    num_handles = m.perform()
    if num_handles == 0:
        break
m.remove_handle(c2)
m.remove_handle(c1)
m.cleanup()
c1.cleanup()
c2.cleanup()
