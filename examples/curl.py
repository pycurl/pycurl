#! /usr/bin/env python
# vi:ts=4:et
# $Id$

# We should ignore SIGPIPE when using pycurl.NOSIGNAL - see the libcurl
# documentation `libcurl-the-guide' for more info.
try:
    import signal
    from signal import SIGPIPE, SIG_IGN
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except ImportError:
    pass
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import urllib, mimetools
import pycurl


class Curl:
    def __init__(self, url, file=None, data=None):
        self.h = []
        self.status = None
        self.server_reply = StringIO()
        self.c = pycurl.Curl()
        self.url = url
        self.data = data
        self.c.setopt(pycurl.URL, self.url)
        self.c.setopt(pycurl.NOSIGNAL, 1)
        self.c.setopt(pycurl.HEADERFUNCTION, self.server_reply.write)

        if file is None:
            self.fp = StringIO()
            self.c.setopt(pycurl.WRITEFUNCTION, self.fp.write)
        else:
            self.fp = file
            self.c.setopt(pycurl.WRITEDATA, self.fp)
        if self.data != None:
            self.c.setopt(pycurl.POST, 1)
            self.c.setopt(pycurl.POSTFIELDS, urllib.urlencode(self.data))

    def set_url(self, url):
        self.c.setopt(pycurl.URL, url)
        self.url = url

    def add_header(self, *args):
        self.h.append(args[0] + ': ' +args[1])

    def retrieve(self, timeout=30):
        if self.h:
            self.c.setopt(pycurl.HTTPHEADER, self.h)
        self.c.setopt(pycurl.CONNECTTIMEOUT, timeout)
        self.c.setopt(pycurl.TIMEOUT, timeout)
        self.c.perform()
        self.fp.seek(0,0)
        return (self.fp, self.info())

    def info(self):
        self.server_reply.seek(0,0)
        url = self.c.getinfo(pycurl.EFFECTIVE_URL)
        if url[:5] == 'http:':
            self.server_reply.readline()
        m = mimetools.Message(self.server_reply)
        m['effective-url'] = url
        m['http-code'] = str(self.c.getinfo(pycurl.HTTP_CODE))
        m['total-time'] = str(self.c.getinfo(pycurl.TOTAL_TIME))
        m['namelookup-time'] = str(self.c.getinfo(pycurl.NAMELOOKUP_TIME))
        m['connect-time'] = str(self.c.getinfo(pycurl.CONNECT_TIME))
        m['pretransfer-time'] = str(self.c.getinfo(pycurl.PRETRANSFER_TIME))
        m['redirect-time'] = str(self.c.getinfo(pycurl.REDIRECT_TIME))
        m['redirect-count'] = str(self.c.getinfo(pycurl.REDIRECT_COUNT))
        m['size-upload'] = str(self.c.getinfo(pycurl.SIZE_UPLOAD))
        m['size-download'] = str(self.c.getinfo(pycurl.SIZE_DOWNLOAD))
        m['speed-upload'] = str(self.c.getinfo(pycurl.SPEED_UPLOAD))
        m['header-size'] = str(self.c.getinfo(pycurl.HEADER_SIZE))
        m['request-size'] = str(self.c.getinfo(pycurl.REQUEST_SIZE))
        m['content-length-download'] = str(self.c.getinfo(pycurl.CONTENT_LENGTH_DOWNLOAD))
        m['content-length-upload'] = str(self.c.getinfo(pycurl.CONTENT_LENGTH_UPLOAD))
        m['content-type'] = self.c.getinfo(pycurl.CONTENT_TYPE) or ''
        return m

    def close(self):
        self.c.close()
        self.server_reply.close()
        self.fp.close()

    def __del__(self):
        self.close()


if __name__ == "__main__":
    c = Curl('http://curl.haxx.se/')
    file, info = c.retrieve()
    print file.read()
    print '='*74 + '\n'
    print info
    c.close()
