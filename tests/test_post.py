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

c = pycurl.init()
c.setopt(pycurl.URL, 'http://pycurl.sourceforge.net/tests/testpostvars.php')
c.setopt(pycurl.POST, 1)
c.setopt(pycurl.POSTFIELDS, urllib.urlencode(pf))
c.perform()
c.cleanup()
