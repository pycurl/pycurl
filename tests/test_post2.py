#! /usr/bin/env python
# vi:ts=4:et
# $Id$

import pycurl


pf = ['field1=this is a test using httppost & stuff', 'field2=value2']

c = pycurl.Curl()
c.setopt(c.URL, 'http://www.contactor.se/~dast/postit.cgi')
c.setopt(c.HTTPPOST, pf)
c.setopt(c.VERBOSE, 1)
c.perform()
c.close()
