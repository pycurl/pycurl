#! /usr/bin/env python
"""WebSocket client that reassembles fragmented frames (detached mode).

Loops ws_recv() with a small buffer until meta.bytesleft == 0.
"""

import pycurl

c = pycurl.Curl()
c.setopt(c.URL, "wss://echo.websocket.events/")
c.setopt(c.CONNECT_ONLY, 2)
c.perform()

c.ws_send("send me a long reply" * 32)  # str -> WS_TEXT

parts = []
while True:
    chunk, meta = c.ws_recv(64)
    parts.append(chunk)
    if meta.bytesleft == 0:
        break

message = b"".join(parts)
print("reassembled %d bytes, last flags=%#x" % (len(message), meta.flags))

c.ws_close()
c.close()
