# $Id$

import pycurl

pf = ['field1=this is a test using httppost & stuff', 'field2=value2']

c = pycurl.init()
c.setopt(pycurl.URL, 'http://pycurl.sourceforge.net/tests/testpostvars.php')
c.setopt(pycurl.POST, 1)
c.setopt(pycurl.HTTPPOST, pf)
c.perform()
c.cleanup()
