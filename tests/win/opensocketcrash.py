import pycurl
from io import BytesIO
import socket

def socket_open(family, socktype, protocol, address):
    global socket_open_called
    global socket_open_address
    socket_open_called = True
    socket_open_address = address
    
    #print(family, socktype, protocol, address)
    s = socket.socket(family, socktype, protocol)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    print(2)
    return s 

curl = pycurl.Curl() 
curl.setopt(pycurl.OPENSOCKETFUNCTION, socket_open)
curl.setopt(curl.URL, 'http://localhost:8380/success')
sio = BytesIO()
curl.setopt(pycurl.WRITEFUNCTION, sio.write)
print(1)
curl.perform()
print(1)

assert socket_open_called
assertEqual(("127.0.0.1", 8380), socket_open_address)
assertEqual('success', sio.getvalue().decode()) 

print(1)
