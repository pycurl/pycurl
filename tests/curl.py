# $Id$

## System modules
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import urllib, mimetools

## PycURL module
import pycurl


class Curl:

    def __init__(self, url, file=None, data=None):
        self.h = []
        self.status = None
        self.server_reply = StringIO()
        self.c = pycurl.init()
        self.url = url
        self.data = data
        self.c.setopt(pycurl.URL, self.url)
        self.c.setopt(pycurl.HEADERFUNCTION, self.server_reply.write)

        if file == None:
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

    def add_header(self, *args):
        self.h.append(args[0] + ': ' +args[1])

    def retrieve(self):
        if self.h != []:
            self.c.setopt(pycurl.HTTPHEADER, self.h)
        self.c.perform()
        self.fp.seek(0,0)
        return (self.fp, self.info())

    def info(self):
        self.server_reply.seek(0,0)
        self.server_reply.readline() # FIXME: won't work well on non-http headers 
        m = mimetools.Message(self.server_reply)
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
        m['effective-url'] = self.c.getinfo(pycurl.EFFECTIVE_URL)
        m['content-type'] = self.c.getinfo(pycurl.CONTENT_TYPE)
        return m

    def close(self):
        self.c.cleanup()
        self.server_reply.close()
        self.fp.close()

    def __del__(self):
        self.close()


if __name__ == "__main__":
    c = Curl('http://curl.haxx.se/')
    file, info = c.retrieve()
    print info, file.read()
    c.close()
