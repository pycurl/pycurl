# $Id$

## System modules
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import urllib

## PycURL module
import pycurl


class Curl:

    def __init__(self, url, filename=None, data=None):
        self.h = []
        self.status = None

        self.c = pycurl.init()
        self.url = url
        self.data = data
        self.c.setopt(pycurl.URL, self.url)

        if filename == None:
            self.fp = StringIO()
            self.c.setopt(pycurl.WRITEFUNCTION, self.fp.write)
        else:
            self.fp = open(filename, 'w')
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
        self.status = self.c.getinfo(pycurl.HTTP_CODE)
        return self.status

    def close(self):
        self.c.cleanup()
        self.fp.close()

    def __del__(self):
        self.close()


if __name__ == "__main__":
    c = Curl('http://curl.haxx.se')
    c.retrieve()
    c.close()
