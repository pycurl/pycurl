#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

import pycurl

m = pycurl.CurlMulti()
m.handles = []
c1 = pycurl.Curl()
c2 = pycurl.Curl()
c1.setopt(c1.URL, 'http://curl.haxx.se')
c2.setopt(c2.URL, 'http://cnn.com')
c2.setopt(c2.FOLLOWLOCATION, 1)
m.add_handle(c1)
m.add_handle(c2)
m.handles.append(c1)
m.handles.append(c2)

num_handles = len(m.handles)
while num_handles:
    while 1:
        ret, num_handles = m.perform()
        if ret != pycurl.E_CALL_MULTI_PERFORM:
            break
    m.select(1.0)

m.remove_handle(c2)
m.remove_handle(c1)
del m.handles
m.close()
c1.close()
c2.close()
