# $Id$

import pycurl
m = pycurl.multi_init()
c = pycurl.init()
c.setopt(pycurl.URL, 'http://curl.haxx.se')
m.add_handle(c)
while 1:
    num_handles = m.perform()
    if num_handles == 0:
        break
m.remove_handle(c)
m.cleanup()
c.cleanup()
