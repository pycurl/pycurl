#! /usr/bin/env python
"""Drive several WebSocket connections concurrently with CurlMulti.

The handshake runs through the multi interface; once every handle has
completed the upgrade, we select() on the underlying sockets and use
ws_send / ws_recv on whichever handle becomes readable.
"""

import select
import pycurl

URLS = ["wss://echo.websocket.events/"] * 3

handles = []
m = pycurl.CurlMulti()
for url in URLS:
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.CONNECT_ONLY, 2)
    m.add_handle(c)
    handles.append(c)

# Drive the handshakes concurrently via the multi interface.
_, num_handles = m.perform()
while num_handles:
    m.select(1.0)
    _, num_handles = m.perform()

# Every handle has finished the WebSocket upgrade — collect results.
_, done, failed = m.info_read()
if failed:
    raise RuntimeError("WebSocket handshake failed: %r" % (failed,))

fd_to_curl = {c.getinfo(pycurl.ACTIVESOCKET): c for c in handles}
for c in handles:
    c.ws_send("hello")

# Read one reply from each handle. A real application would keep
# looping on select() for as long as it has work to do; this demo
# simply waits until each connection has produced its echoed frame.
pending = set(fd_to_curl)
while pending:
    readable, _, _ = select.select(list(pending), [], [], 5.0)
    if not readable:
        raise TimeoutError("no reply within 5s for handles %r" % (pending,))
    for fd in readable:
        data, meta = fd_to_curl[fd].ws_recv(4096)
        print(fd, data, "flags=", meta.flags)
        pending.discard(fd)

for c in handles:
    c.ws_close()
    m.remove_handle(c)
    c.close()
m.close()
