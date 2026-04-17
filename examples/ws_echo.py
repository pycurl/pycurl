#! /usr/bin/env python
"""Minimal WebSocket echo client (detached mode)."""

import pycurl

c = pycurl.Curl()
c.setopt(c.URL, "wss://echo.websocket.events/")
c.setopt(c.CONNECT_ONLY, 2)
c.perform()

c.ws_send("hello")  # str -> WS_TEXT (UTF-8 encoded)
data, meta = c.ws_recv(4096)
print("recv:", data, "flags:", meta.flags)

c.ws_close(1000, "normal closure")
c.close()
