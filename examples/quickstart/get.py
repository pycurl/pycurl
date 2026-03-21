#! /usr/bin/env python
# vi:ts=4:et

import pycurl
from io import BytesIO

buffer = BytesIO()
c = pycurl.Curl()
c.setopt(c.URL, 'http://pycurl.io/')
c.setopt(c.WRITEDATA, buffer)
# For older PycURL versions:
#c.setopt(c.WRITEFUNCTION, buffer.write)
c.perform()
c.close()

body = buffer.getvalue()
# Body is a byte string.
# If we know the encoding, we can always decode the body and
# end up with a Unicode string.
print(body.decode('iso-8859-1'))
