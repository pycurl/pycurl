# $Id$

## PycURL module
import pycurl

## XML-RPC lib included in python2.2
import xmlrpclib

# Header fields passed in request
xmlrpc_header = [
    "User-Agent: PycURL XML-RPC Test", "Content-Type: text/xml"
    ]

# XML-RPC request template
xmlrpc_template = """
<?xml version='1.0'?><methodCall><methodName>%s</methodName>%s</methodCall>
"""

# Engage
c = pycurl.init()
c.setopt(pycurl.URL, 'http://betty.userland.com/RPC2')
c.setopt(pycurl.POST, 1)
c.setopt(pycurl.HTTPHEADER, xmlrpc_header)
req = xmlrpc_template % ("examples.getStateName", xmlrpclib.dumps((5,)))
c.setopt(pycurl.POSTFIELDS, req)

print 'Response from http://betty.userland.com/'
c.perform()
c.cleanup()
