# A high-level interface to the pycurl extension
#
# ** mfx NOTE: the CGI class uses "black magic" using COOKIEFILE in
#    combination with a non-existant file name. See the libcurl docs
#    for more info.
#
# If you want thread-safe operation, you'll have to set the NOSIGNAL option
# yourself.
#
# By Eric S. Raymond, April 2003.

import os, sys, urllib, exceptions, mimetools, pycurl
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

class Curl:
    "High-level interface to cURL functions."
    def __init__(self, base_url="", fakeheaders=[]):
        self.handle = pycurl.Curl()
        # These members might be set.
        self.set_url(base_url)
        self.verbosity = 0
        self.fakeheaders = fakeheaders
        # Nothing past here should be modified by the caller.
        self.payload = ""
        self.header = StringIO()
        # Verify that we've got the right site; harmless on a non-SSL connect.
        self.set_option(pycurl.SSL_VERIFYHOST, 2)
        # Follow redirects in case it wants to take us to a CGI...
        self.set_option(pycurl.FOLLOWLOCATION, 1)
        self.set_option(pycurl.MAXREDIRS, 5)
        # Setting this option with even a nonexistent file makes libcurl
        # handle cookie capture and playback automatically.
        self.set_option(pycurl.COOKIEFILE, "/dev/null")
        # Set timeouts to avoid hanging too long
        self.set_option(pycurl.CONNECTTIMEOUT, 30)
        self.set_option(pycurl.TIMEOUT, 300)
        # Use password identification from .netrc automatically
        self.set_option(pycurl.NETRC, 1)
        # Set up a callback to capture the payload
        def payload_callback(x):
            self.payload += x
        self.set_option(pycurl.WRITEFUNCTION, payload_callback)
        def header_callback(x):
            self.header.write(x)
        self.set_option(pycurl.HEADERFUNCTION, header_callback)

    def set_url(self, url):
        "Set the base URL to be retrieved."
        self.base_url = url
        self.set_option(pycurl.URL, self.base_url)

    def set_option(self, *args):
        "Set an option on the retrieval,"
        apply(self.handle.setopt, args)

    def set_verbosity(self, level):
        "Set verbosity to 1 to see transactions."
        self.set_option(pycurl.VERBOSE, level)

    def __request(self, relative_url=None):
        "Perform the pending request."
        if self.fakeheaders:
            self.set_option(pycurl.HTTPHEADER, self.fakeheaders)
        if relative_url:
            self.set_option(pycurl.URL,os.path.join(self.base_url,relative_url))
        self.header.seek(0,0)
        self.payload = ""
        self.handle.perform()
        return self.payload

    def get(self, url="", params=None):
        "Ship a GET request for a specified URL, capture the response."
        if params:
            url += "?" + urllib.urlencode(params)
        self.set_option(pycurl.HTTPGET, 1)
        return self.__request(url)

    def post(self, cgi, params):
        "Ship a POST request to a specified CGI, capture the response."
        self.set_option(pycurl.POST, 1)
        self.set_option(pycurl.POSTFIELDS, urllib.urlencode(params))
        return self.__request(cgi)

    def body(self):
        "Return the body from the last response."
        return self.payload

    def info(self):
        "Return an RFC822 object with info on the page."
        self.header.seek(0,0)
        url = self.handle.getinfo(pycurl.EFFECTIVE_URL)
        if url[:5] == 'http:':
            self.header.readline()
            m = mimetools.Message(self.header)
        else:
            m = mimetools.Message(StringIO())
        m['effective-url'] = url
        m['http-code'] = str(self.handle.getinfo(pycurl.HTTP_CODE))
        m['total-time'] = str(self.handle.getinfo(pycurl.TOTAL_TIME))
        m['namelookup-time'] = str(self.handle.getinfo(pycurl.NAMELOOKUP_TIME))
        m['connect-time'] = str(self.handle.getinfo(pycurl.CONNECT_TIME))
        m['pretransfer-time'] = str(self.handle.getinfo(pycurl.PRETRANSFER_TIME))
        m['redirect-time'] = str(self.handle.getinfo(pycurl.REDIRECT_TIME))
        m['redirect-count'] = str(self.handle.getinfo(pycurl.REDIRECT_COUNT))
        m['size-upload'] = str(self.handle.getinfo(pycurl.SIZE_UPLOAD))
        m['size-download'] = str(self.handle.getinfo(pycurl.SIZE_DOWNLOAD))
        m['speed-upload'] = str(self.handle.getinfo(pycurl.SPEED_UPLOAD))
        m['header-size'] = str(self.handle.getinfo(pycurl.HEADER_SIZE))
        m['request-size'] = str(self.handle.getinfo(pycurl.REQUEST_SIZE))
        m['content-length-download'] = str(self.handle.getinfo(pycurl.CONTENT_LENGTH_DOWNLOAD))
        m['content-length-upload'] = str(self.handle.getinfo(pycurl.CONTENT_LENGTH_UPLOAD))
        m['content-type'] = (self.handle.getinfo(pycurl.CONTENT_TYPE) or '').strip(';')
        return m

    def answered(self, check):
        "Did a given check string occur in the last payload?"
        return self.payload.find(check) >= 0

    def close(self):
        "Close a session, freeing resources."
        self.handle.close()
        self.header.close()

    def __del__(self):
        self.close()

if __name__ == "__main__":
    c = Curl()
    c.get('http://curl.haxx.se/')
    print c.body()
    print '='*74 + '\n'
    print c.info()
    c.close()
