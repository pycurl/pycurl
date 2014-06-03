#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import pycurl
import zlib
try:
    from io import BytesIO
except ImportError:
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from StringIO import StringIO as BytesIO

c = pycurl.Curl()
c.setopt(c.URL, 'http://pycurl.sourceforge.net')
#c.setopt(c.ENCODING, 'deflate')
c.setopt(c.HTTPHEADER, ['Accept-Encoding: deflate'])
body = BytesIO()
c.setopt(c.WRITEFUNCTION, body.write)
encoding_found = False
def header_function(header):
    global encoding_found
    if header.decode('iso-8859-1').lower().startswith('content-encoding: deflate'):
        encoding_found = True
c.setopt(c.HEADERFUNCTION, header_function)
c.perform()
assert encoding_found
print('Server supports deflate encoding')
encoded = body.getvalue()
# should not raise exceptions
zlib.decompress(encoded, -zlib.MAX_WBITS)
print('Server served deflated body')

c.reset()
c.setopt(c.URL, 'http://pycurl.sourceforge.net')
c.setopt(c.ENCODING, 'deflate')
body = BytesIO()
c.setopt(c.WRITEFUNCTION, body.write)
encoding_found = False
def header_function(header):
    global encoding_found
    if header.decode('iso-8859-1').lower().startswith('content-encoding: deflate'):
        encoding_found = True
c.setopt(c.HEADERFUNCTION, header_function)
c.perform()
assert encoding_found
print('Server claimed deflate encoding as expected')
# body should be decoded
encoded = body.getvalue()
if '<html' in encoded.decode('iso-8859-1').lower():
    print('Curl inflated served body')
else:
    fail = False
    try:
        zlib.decompress(encoded, -zlib.MAX_WBITS)
        print('Curl did not inflate served body')
        fail = True
    except:
        print('Weird')
        fail = True
    if fail:
        assert False

c.close()
