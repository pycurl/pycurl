from _pycurl import *

# A high-level interface to the pycurl extension
#
# ** mfx NOTE: the CGI class uses "black magic" using COOKIEFILE in
#    combination with a non-existant file name. See the libcurl docs
#    for more info.
#
# By Eric S. Raymond, April 2003.

import os, sys, urllib, exceptions

class CGIClient:
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
