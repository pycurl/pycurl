#! /usr/bin/env python
# vi:ts=4:et

import pycurl
import zlib
from io import BytesIO

c = pycurl.Curl()
c.setopt(c.URL, 'http://pycurl.io')
#c.setopt(c.ENCODING, 'deflate')
c.setopt(c.HTTPHEADER, ['Accept-Encoding: deflate'])
body = BytesIO()
c.setopt(c.WRITEFUNCTION, body.write)
c.perform()
c.close()

body = body.getvalue()
print(len(body))
# Content should be deflate-encoded
body = zlib.decompress(body, -zlib.MAX_WBITS)
print(len(body))
