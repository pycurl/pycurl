import pycurl
import StringIO
import socket

def socketopen(family, socktype, protocol):
    print family, socktype, protocol
    s = socket.socket(family, socktype, protocol)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    return s

sio = StringIO.StringIO()

c = pycurl.Curl()
c.setopt(pycurl.OPENSOCKETFUNCTION, socketopen)
c.setopt(pycurl.URL, 'http://camvine.com')
c.setopt(pycurl.WRITEFUNCTION, sio.write)
c.perform()
