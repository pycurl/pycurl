import curl

f = open('output', 'w')

c = curl.init()
c.setopt(curl.URL, 'http://www.python.org')
c.setopt(curl.FILE, f)
c.setopt(curl.NOPROGRESS, 1)
c.setopt(curl.FOLLOWLOCATION, 1)
c.setopt(curl.MAXREDIRS, 5)
c.perform()

print 'Download speed:', c.getinfo(curl.SPEED_DOWNLOAD)
print 'Document size:', c.getinfo(curl.SIZE_DOWNLOAD)
print 'Effective URL:', c.getinfo(curl.EFFECTIVE_URL)

c.cleanup()
