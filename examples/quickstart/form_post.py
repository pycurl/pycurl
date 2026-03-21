#! /usr/bin/env python
# vi:ts=4:et

import pycurl
from urllib.parse import urlencode

c = pycurl.Curl()
c.setopt(c.URL, 'https://httpbin.org/post')

post_data = {'field': 'value'}
# Form data must be provided already urlencoded.
postfields = urlencode(post_data)
# Sets request method to POST,
# Content-Type header to application/x-www-form-urlencoded
# and data to send in request body.
c.setopt(c.POSTFIELDS, postfields)

c.perform()
c.close()
