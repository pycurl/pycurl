# $Id$

import pycurl

pf = ['field1=this is a test using httppost & stuff', 'field2=value2']

c = pycurl.Curl()
c.setopt(c.URL, 'http://pycurl.sourceforge.net/tests/testpostvars.php')
c.setopt(c.POST, 1)
c.setopt(c.HTTPPOST, pf)
c.perform()
c.close()
