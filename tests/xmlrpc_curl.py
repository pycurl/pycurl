import xmlrpclib, pycurl, cStringIO

class CURLTransport(xmlrpclib.Transport):
    """Handles an HTTP transaction to an XML-RPC server."""

    xmlrpc_headers = [
        "User-Agent: PycURL XML-RPC", "Content-Type: text/xml"
        ]

    def __init__(self, username=None, password=None):
        self.c = pycurl.init()
        if username != None and password != None:
            self.c.setopt(pycurl.USERPWD, '%s:%s' % (username, password))

    def request(self, host, handler, request_body, verbose=0):
        b = cStringIO.StringIO()
        self.c.setopt(pycurl.URL, 'http://%s%s' % (host, handler))
        self.c.setopt(pycurl.POST, 1)
        self.c.setopt(pycurl.HTTPHEADER, self.xmlrpc_headers)
        self.c.setopt(pycurl.POSTFIELDS, request_body)
        self.c.setopt(pycurl.WRITEFUNCTION, b.write)
        self.c.setopt(pycurl.VERBOSE, verbose)
        self.verbose = verbose
        try:
            self.c.perform()
        except pycurl.error, v:
            raise ProtocolError(
                host + handler,
                -1, v, None
                )
        b.seek(0)
        return self.parse_response(b)


if __name__ == "__main__":
    server = xmlrpclib.ServerProxy("http://betty.userland.com",
                                   transport=CURLTransport())

    print server

    try:
        print server.examples.getStateName(41)
        print server.examples.getStateName(41)
        print server.examples.getStateName(41)
        print server.examples.getStateName(41)
    except xmlrpclib.Error, v:
        print "ERROR", v
