from _pycurl import *

# A high-level interface to the pycurl extension
#
# ** mfx NOTE: the CGI class uses "black magic" using COOKIEFILE in
#    combination with a non-existant file name. See the libcurl docs
#    for more info.
#
# By Eric S. Raymond, April 2003.

import os, sys, urllib, exceptions

class CurlCGI:
    "Encapsulate user operations on CGIs through cURL."
    def __init__(self, base_url=""):
        # These members might be set.
        self.base_url = base_url
        self.verbosity = 0
        # Nothing past here should be modified by the caller.
        self.response = ""
        self.curlobj = Curl()
        # Verify that we've got the right site; harmless on a non-SSL connect.
        self.curlobj.setopt(SSL_VERIFYHOST, 2)
        # Follow redirects in case it wants to take us to a CGI...
        self.curlobj.setopt(FOLLOWLOCATION, 1)
        self.curlobj.setopt(MAXREDIRS, 5)
        # Setting this option with even a nonexistent file makes libcurl
        # handle cookie capture and playback automatically.
        self.curlobj.setopt(COOKIEFILE, "/dev/null")
        # Set timeouts to avoid hanging too long
        self.curlobj.setopt(CONNECTTIMEOUT, 30)
        self.curlobj.setopt(TIMEOUT, 300)
        # Use password identification from .netrc automatically
        self.curlobj.setopt(NETRC, 1)
        # Set up a callback to capture the response
        def response_callback(x):
            self.response += x
        self.curlobj.setopt(WRITEFUNCTION, response_callback)
    def set_verbosity(self, level):
        "Set verbosity to 1 to see transactions."
        self.curlobj.setopt(VERBOSE, level)
    def get(self, cgi, params=""):
        "Ship a GET request to a specified CGI, capture the response body."
        if params:
            cgi += "?" + urllib.urlencode(params)
        self.curlobj.setopt(URL, os.path.join(self.base_url, cgi))
        self.curlobj.setopt(HTTPGET, 1)
        self.response = ""
        self.curlobj.perform()
    def post(self, cgi, params):
        "Ship a POST request to a specified CGI, capture the response body.."
        self.curlobj.setopt(URL, os.path.join(self.base_url, cgi))
        self.curlobj.setopt(POST, 1)
        self.curlobj.setopt(POSTFIELDS, urllib.urlencode(params))
        self.response = ""
        self.curlobj.perform()
    def answered(self, check):
        "Did a given check string occur in the last response?"
        return self.response.find(check) >= 0
    def close(self):
        "Close a session, freeing resources."
        self.curlobj.close()

# We should ignore SIGPIPE when using pycurl.NOSIGNAL - see the libcurl
# documentation `libcurl-the-guide' for more info.
try:
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except ImportError:
    pass
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import mimetools

class HiCurl:
    def __init__(self, url, file=None, data=None):
        self.h = []
        self.status = None
        self.server_reply = StringIO()
        self.c = Curl()
        self.url = url
        self.data = data
        self.c.setopt(URL, self.url)
        self.c.setopt(NOSIGNAL, 1)
        self.c.setopt(HEADERFUNCTION, self.server_reply.write)

        if file is None:
            self.fp = StringIO()
            self.c.setopt(WRITEFUNCTION, self.fp.write)
        else:
            self.fp = file
            self.c.setopt(WRITEDATA, self.fp)
        if self.data != None:
            self.c.setopt(POST, 1)
            self.c.setopt(POSTFIELDS, urllib.urlencode(self.data))

    def set_url(self, url):
        "Set the URL to be fetched,"
        self.c.setopt(URL, url)
        self.url = url

    def add_header(self, *args):
        "Add a header to the message object representing info about the URL."
        self.h.append(args[0] + ': ' +args[1])

    def retrieve(self, timeout=30):
        "Perform the page retrieval."
        if self.h:
            self.c.setopt(HTTPHEADER, self.h)
        self.c.setopt(CONNECTTIMEOUT, timeout)
        self.c.perform()
        self.fp.seek(0,0)
        return (self.fp, self.info())

    def info(self):
        "Return an RFC822 object with info on the page."
        self.server_reply.seek(0,0)
        url = self.c.getinfo(EFFECTIVE_URL)
        if url[:5] == 'http:':
            self.server_reply.readline()
            m = mimetools.Message(self.server_reply)
        else:
            m = mimetools.Message(StringIO())
        m['effective-url'] = url
        m['http-code'] = str(self.c.getinfo(HTTP_CODE))
        m['total-time'] = str(self.c.getinfo(TOTAL_TIME))
        m['namelookup-time'] = str(self.c.getinfo(NAMELOOKUP_TIME))
        m['connect-time'] = str(self.c.getinfo(CONNECT_TIME))
        m['pretransfer-time'] = str(self.c.getinfo(PRETRANSFER_TIME))
        m['redirect-time'] = str(self.c.getinfo(REDIRECT_TIME))
        m['redirect-count'] = str(self.c.getinfo(REDIRECT_COUNT))
        m['size-upload'] = str(self.c.getinfo(SIZE_UPLOAD))
        m['size-download'] = str(self.c.getinfo(SIZE_DOWNLOAD))
        m['speed-upload'] = str(self.c.getinfo(SPEED_UPLOAD))
        m['header-size'] = str(self.c.getinfo(HEADER_SIZE))
        m['request-size'] = str(self.c.getinfo(REQUEST_SIZE))
        m['content-length-download'] = str(self.c.getinfo(CONTENT_LENGTH_DOWNLOAD))
        m['content-length-upload'] = str(self.c.getinfo(CONTENT_LENGTH_UPLOAD))
        m['content-type'] = (self.c.getinfo(CONTENT_TYPE) or '').strip(';')
        return m

    def get_server_reply(self):
        self.server_reply.seek(0,0)
        return self.server_reply.getvalue()

    def close(self):
        self.c.close()
        self.server_reply.close()
        self.fp.close()

    def __del__(self):
        self.close()
