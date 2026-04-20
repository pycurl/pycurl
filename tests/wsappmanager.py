"""Lightweight asyncio websockets test server used by ws tests."""

import asyncio
import threading
import warnings
from typing import Optional


class WsServer:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._stop: Optional[asyncio.Future] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=10.0):
            raise RuntimeError("ws test server failed to start")

    def stop(self) -> None:
        if self.loop is None or self._stop is None:
            return
        self.loop.call_soon_threadsafe(self._stop.set_result, None)
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                warnings.warn(
                    "ws test server thread did not exit within 5s; "
                    "a background asyncio task may be stuck",
                    ResourceWarning,
                    stacklevel=2,
                )

    def _run(self) -> None:
        import websockets

        async def echo(ws):
            try:
                async for msg in ws:
                    await ws.send(msg)
            except Exception:
                pass

        async def echo_on_connect(ws):
            await ws.send("hello")
            await ws.close()

        async def binary_on_connect(ws):
            await ws.send(b"\x01\x02\x03")
            await ws.close()

        async def fragmented_on_connect(ws):
            await ws.send(["one-", "two-", "three"])
            await ws.close()

        async def silent(ws):
            try:
                async for _ in ws:
                    pass
            except Exception:
                pass

        async def greet_and_echo_reply(ws):
            await ws.send(b"hi")
            reply = await ws.recv()
            assert reply == b"ack", f"expected b'ack', got {reply!r}"
            await ws.close()

        async def greet_and_wait_close(ws):
            await ws.send(b"hi")
            try:
                async for _ in ws:
                    pass
            except Exception:
                pass

        async def greet_and_close(ws):
            await ws.send(b"hi")
            await ws.close()

        async def ping_and_report_pong(ws):
            pong_waiter = await ws.ping(b"probe")
            try:
                await asyncio.wait_for(pong_waiter, timeout=0.5)
                await ws.send("pong-ok")
            except asyncio.TimeoutError:
                await ws.send("pong-missing")
            await ws.close()

        routes = {
            "/echo": echo,
            "/echo-on-connect": echo_on_connect,
            "/binary-on-connect": binary_on_connect,
            "/fragmented-on-connect": fragmented_on_connect,
            "/silent": silent,
            "/greet-and-echo-reply": greet_and_echo_reply,
            "/greet-and-wait-close": greet_and_wait_close,
            "/greet-and-close": greet_and_close,
            "/ping-and-report-pong": ping_and_report_pong,
        }

        async def dispatch(ws):
            path = ws.request.path
            handler = routes.get(path, echo)
            await handler(ws)

        async def main():
            self._stop = asyncio.get_running_loop().create_future()
            async with websockets.serve(dispatch, self.host, self.port):
                self._ready.set()
                await self._stop

        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(main())
        finally:
            if self.loop is not None:
                self.loop.close()


def start_server(host: str, port: int) -> WsServer:
    s = WsServer(host, port)
    s.start()
    return s
