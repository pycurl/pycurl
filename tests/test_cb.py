import curl

def body(buf):
    print buf
    return len(buf)

def header(buf):
    print ':::::::::::', buf
    return len(buf)

c = curl.init()
c.setopt(curl.URL, 'http://www.python.org/')
c.setopt(curl.WRITEFUNCTION, body)
c.setopt(curl.HEADERFUNCTION, header)
c.setopt(curl.NOPROGRESS, 1)
c.setopt(curl.FOLLOWLOCATION, 1)
c.setopt(curl.MAXREDIRS, 5)
c.perform()
c.setopt(curl.URL, 'http://curl.haxx.se/')
c.perform()
c.cleanup()
