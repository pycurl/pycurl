# $Id$

import pycurl

# note: multiple fields are separated by a single '&'
#   FIXME: how can you include a verbatim '&' in a value ??

# simple
pf = 'field1=value1'

# multiple fields
pf = 'field1=value1&field2=value2 with blanks&field3=value3'

c = pycurl.init()
c.setopt(pycurl.URL, 'http://pycurl.sourceforge.net/tests/testpostvars.php')
c.setopt(pycurl.POST, 1)
c.setopt(pycurl.POSTFIELDS, pf)
c.perform()
c.cleanup()
