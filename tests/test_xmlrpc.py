#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

## XML-RPC lib included in python2.2
import xmlrpclib
import pycurl

# Header fields passed in request
xmlrpc_header = [
    "User-Agent: PycURL XML-RPC Test", "Content-Type: text/xml"
    ]

# XML-RPC request template
xmlrpc_template = """
<?xml version='1.0'?><methodCall><methodName>%s</methodName>%s</methodCall>
"""

# Engage
c = pycurl.Curl()
c.setopt(c.URL, 'http://betty.userland.com/RPC2')
c.setopt(c.POST, 1)
c.setopt(c.HTTPHEADER, xmlrpc_header)
c.setopt(c.POSTFIELDS, xmlrpc_template % ("examples.getStateName", xmlrpclib.dumps((5,))))

print 'Response from http://betty.userland.com/'
c.perform()
c.close()
