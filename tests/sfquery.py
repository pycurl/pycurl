#! /usr/bin/env python2.2
#
# sfquery -- Source Forge query script
#
# Requires Python 2.2 or better.
#
# Retrieves a SourceForge XML export object for a given project.
# Specify the *numeric* project ID. the user name, and the password,
# as arguments. If you have a valid ~/.netrc entry for sourceforge.net,
# you can just give the project ID.
#
# Illustrates GET and POST transactions over HTTPS, response callbacks,
# and enabling basic cookie echoing for stateful sessions.
#
# ** mfx NOTE: this program uses "black magic" using COOKIEFILE in
#    combination with a non-existant file name. See the libcurl docs
#    for more info.
#
# By Eric S. Raymond, August 2002.  All rites reversed.

import os, sys, urllib, netrc
import pycurl

class CGIClient:
    "Encapsulate user operations on CGIs through curl."
    def __init__(self, base_url=""):
        # These members might be set.
        self.base_url = base_url
        self.verbosity = 0
        # Nothing past here should be modified by the caller.
        self.response = ""
        self.curlobj = pycurl.Curl()
        # Verify that we've got the right site...
        self.curlobj.setopt(pycurl.SSL_VERIFYHOST, 2)
        # Follow redirects in case it wants to take us to a CGI...
        self.curlobj.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curlobj.setopt(pycurl.MAXREDIRS, 5)
        # Setting this option with even a nonexistent file makes libcurl
        # handle cookie capture and playback automatically.
        self.curlobj.setopt(pycurl.COOKIEFILE, "/dev/null")
        # Set up a callback to capture
        def response_callback(x):
            self.response += x
        self.curlobj.setopt(pycurl.WRITEFUNCTION, response_callback)
    def set_verbosity(self, level):
        "Set verbosity to 1 to see transactions."
        self.curlobj.setopt(pycurl.VERBOSE, level)
    def get(self, cgi, params=""):
        "Ship a GET request to a specified CGI, capture the response body."
        if params:
            cgi += "?" + urllib.urlencode(params)
        self.curlobj.setopt(pycurl.URL, os.path.join(self.base_url, cgi))
        self.curlobj.setopt(pycurl.HTTPGET, 1)
        self.response = ""
        self.curlobj.perform()
    def post(self, cgi, params):
        "Ship a POST request to a specified CGI, capture the response body.."
        self.curlobj.setopt(pycurl.URL, os.path.join(self.base_url, cgi))
        self.curlobj.setopt(pycurl.POST, 1)
        self.curlobj.setopt(pycurl.POSTFIELDS, urllib.urlencode(params))
        self.response = ""
        self.curlobj.perform()
    def answered(self, check):
        "Does a given check string occur in the response?"
        return self.response.find(check) > -1
    def close(self):
        "Close a session, freeing resources."
        self.curlobj.close()

class SourceForgeUserSession(CGIClient):
    # SourceForge-specific methods.  Sensitive to changes in site design.
    def login(self, name, password):
        "Establish a login session."
        self.post("account/login.php", (("form_loginname", name),
                                        ("form_pw", password),
                                        ("return_to", ""),
                                        ("stay_in_ssl", "1"),
                                        ("login", "Login With SSL")))
    def logout(self):
        "Log out of SourceForge."
        self.get("account/logout.php")
    def fetch_xml(self, numid):
        self.get("export/xml_export.php?group_id=%s" % numid)

if __name__ == "__main__":
    project_id = sys.argv[1]
    # Try to grab authenticators out of your .netrc
    auth = netrc.netrc().authenticators("sourceforge.net")
    if auth:
        (name, account, password) = auth
    else:
        name = sys.argv[2]
        password = sys.argv[3]
    session = SourceForgeUserSession('https://sourceforge.net/')
    session.set_verbosity(0)
    session.login(name, password)
    # Login could fail.
    if session.answered("Invalid Password or User Name"):
        sys.stderr.write("Login/password not accepted (%d bytes)\n" % len(session.response))
        raise SystemExit, 1
    # We'll see this if we get the right thing.
    elif session.answered("Personal Page For: " + name):
        session.fetch_xml(project_id)
        sys.stdout.write(session.response)
        session.logout()
        raise SystemExit, 0
    # Or maybe SourceForge has changed its site design so our check strings
    # are no longer valid.
    else:
        sys.stderr.write("Unexpected page (%d bytes)\n"%len(session.response))
        raise SystemExit, 1

# The following sets edit modes for GNU EMACS
# Local Variables:
# mode:python
# End:
