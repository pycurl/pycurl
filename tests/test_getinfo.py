import curl

def progress(total, download):
    print 'total to download %d, have %d so far' % (total, download)
    return 0 # Anything else indicates an error

f = open('body', 'w')
h = open('header', 'w')

c = curl.init()
c.setopt(curl.URL, 'http://www.python.org/')
c.setopt(curl.FILE, f)
c.setopt(curl.PROGRESSFUNCTION, progress)
c.setopt(curl.FOLLOWLOCATION, 1)
c.setopt(curl.MAXREDIRS, 5)
c.setopt(curl.WRITEHEADER, h)
c.perform()

print 'Download speed:', c.getinfo(curl.SPEED_DOWNLOAD)
print 'Document size:', c.getinfo(curl.SIZE_DOWNLOAD)
print 'Effective URL:', c.getinfo(curl.EFFECTIVE_URL)

c.cleanup()
f.close()
h.close()
