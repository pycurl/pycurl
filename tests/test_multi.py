# $Id$

import pycurl

m = pycurl.CurlMulti()
c1 = pycurl.Curl()
c2 = pycurl.Curl()
c1.setopt(c1.URL, 'http://curl.haxx.se')
c2.setopt(c2.URL, 'http://python.org')
m.add_handle(c1)
m.add_handle(c2)
while 1:
    num_handles = m.perform()
    if num_handles == 0:
        break
m.remove_handle(c2)
m.remove_handle(c1)
m.close()
c1.close()
c2.close()
