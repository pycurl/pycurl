#! /usr/bin/env python
"""WebSocket client using callback-receive mode.

This example starts a tiny local websocket server with the ``websockets``
package so the transfer always receives one frame and terminates
predictably.
"""

import asyncio
from pathlib import Path
import socket
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pycurl
import websockets


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _start_server(port):
    ready = threading.Event()
    stop = {}

    def run():
        async def handler(ws):
            await ws.send("hello")
            await ws.close()

        async def main():
            stop["loop"] = asyncio.get_running_loop()
            stop["future"] = asyncio.get_running_loop().create_future()
            async with websockets.serve(handler, "127.0.0.1", port):
                ready.set()
                await stop["future"]

        asyncio.run(main())

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    if not ready.wait(5.0):
        raise RuntimeError("server failed to start")
    return thread, stop


port = _free_port()
thread, stop = _start_server(port)
c = pycurl.Curl()


def on_ws_chunk(data):
    meta = c.ws_meta()
    if meta is not None:
        if meta.flags & pycurl.WS_TEXT:
            kind = "text"
        elif meta.flags & pycurl.WS_BINARY:
            kind = "binary"
        elif meta.flags & pycurl.WS_CLOSE:
            kind = "close"
        else:
            kind = "control"
        print("%s chunk len=%d bytesleft=%d" % (kind, len(data), meta.bytesleft))
    return len(data)


try:
    c.setopt(c.URL, "ws://127.0.0.1:%d" % port)
    c.setopt(c.WRITEFUNCTION, on_ws_chunk)
    c.perform()
finally:
    c.close()
    stop["loop"].call_soon_threadsafe(stop["future"].set_result, None)
    thread.join(timeout=5.0)
