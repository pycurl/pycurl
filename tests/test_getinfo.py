# $Id$

## PycURL module
import pycurl

## Callback function invoked when progress information is updated
def progress(download_t, download_d, upload_t, upload_d):
    print 'Total to download %d bytes, have %d bytes so far' % \
          (download_t, download_d)

url = 'http://www.cnn.com'

print 'Starting downloading', url
print
f = open('body', 'w')
h = open('header', 'w')
c = pycurl.init()
c.setopt(pycurl.URL, url)
c.setopt(pycurl.FILE, f)
c.setopt(pycurl.NOPROGRESS, 0)
c.setopt(pycurl.PROGRESSFUNCTION, progress)
c.setopt(pycurl.FOLLOWLOCATION, 1)
c.setopt(pycurl.MAXREDIRS, 5)
c.setopt(pycurl.WRITEHEADER, h)
c.setopt(pycurl.OPT_FILETIME, 1)
c.perform()

print
print 'Download speed: %f bytes/second' % c.getinfo(pycurl.SPEED_DOWNLOAD)
print 'Document size: %d bytes' % c.getinfo(pycurl.SIZE_DOWNLOAD)
print 'Effective URL:', c.getinfo(pycurl.EFFECTIVE_URL)
print 'Content-type:', c.getinfo(pycurl.CONTENT_TYPE)
print 'Redirect-time:', c.getinfo(pycurl.REDIRECT_TIME)
print 'Redirect-count:', c.getinfo(pycurl.REDIRECT_COUNT)
print 'Filetime:', c.getinfo(pycurl.INFO_FILETIME)
print
print "Header is in file 'header', body is in file 'body'"

c.cleanup()
f.close()
h.close()
