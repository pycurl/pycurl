# $Id$
# Python code to http post a file using the following form
# Written by Amit Mongia
"""
<form name="form1" method="post"
action="http://mywebsite.com/uploadfile/using/codeword/"
enctype="multipart/form-data">
  <p>Codeword:
    <input type="text" name="codeword" value="uploadfile">
  </p>
  <p> File to upload:
    <input type="file" name="file">
  </p>
  <p>
    <input type="submit" name="Submit" value="Submit">
  </p>
</form>
"""


import sys
import pycurl

class Test:
    def __init__(self):
        self.contents = ''

    def body_callback(self, buf):
        self.contents = self.contents + buf

print 'Testing', pycurl.version

# The codeword to upload file.
codeword = "uploadfile"

# This is the tricky part. Just give the filename.
# In actual code - use system independent path delimiter
file = "file=@C:\upload.gif"

# Enter the url to upload the file to
put_url = 'http://mywebsite.com/uploadfile/using/codeword/'

t = test()
c = Curl()
c.setopt(pycurl.URL, put_url)
c.setopt(pycurl.WRITEFUNCTION, t.body_callback)
c.setopt(pycurl.HTTPPOST, [token, file])

c.perform()
c.close()

print t.contents

