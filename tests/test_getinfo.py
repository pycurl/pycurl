import pycurl

def progress(total, download, upload_t, upload_d):
    print 'total to download %d, have %d so far' % (total, download)
    return 0 # Anything else indicates an error

f = open('body', 'w')
h = open('header', 'w')

c = pycurl.init()
c.setopt(pycurl.URL, 'http://curl.haxx.se')
c.setopt(pycurl.FILE, f)
c.setopt(pycurl.NOPROGRESS, 0)
c.setopt(pycurl.PROGRESSFUNCTION, progress)
c.setopt(pycurl.FOLLOWLOCATION, 1)
c.setopt(pycurl.MAXREDIRS, 5)
c.setopt(pycurl.WRITEHEADER, h)
c.perform()

print 'Download speed:', c.getinfo(pycurl.SPEED_DOWNLOAD)
print 'Document size:', c.getinfo(pycurl.SIZE_DOWNLOAD)
print 'Effective URL:', c.getinfo(pycurl.EFFECTIVE_URL)
print
print "Header is in file 'header', body is in file 'body'"

c.cleanup()
f.close()
h.close()
