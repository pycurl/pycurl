#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

import pycurl

pf = [('field1', 'this is a test using httppost & stuff'),
      ('field2', (pycurl.FORM_FILE, 'test_post.py', pycurl.FORM_FILE, 'test_post2.py')),
      ('field3', (pycurl.FORM_CONTENTS, 'this is wei\000rd, but null-bytes are okay'))
     ]

c = pycurl.Curl()
c.setopt(c.URL, 'http://www.contactor.se/~dast/postit.cgi')
c.setopt(c.HTTPPOST, pf)
c.setopt(c.VERBOSE, 1)
c.perform()
c.close()
