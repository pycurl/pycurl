#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

import urllib
import pycurl

# simple
pf = {'field1': 'value1'}

# multiple fields
pf = {'field1':'value1', 'field2':'value2 with blanks', 'field3':'value3'}

# multiple fields with & in field
pf = {'field1':'value1', 'field2':'value2 with blanks and & chars',
      'field3':'value3'}

c = pycurl.Curl()
c.setopt(c.URL, 'http://pycurl.sourceforge.net/tests/testpostvars.php')
c.setopt(c.POSTFIELDS, urllib.urlencode(pf))
c.setopt(c.VERBOSE, 1)
c.perform()
c.close()
