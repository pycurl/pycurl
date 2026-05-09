"""Asyncio integration for ``pycurl.CurlMulti``.

Drives :py:class:`pycurl.CurlMulti` transfers from an asyncio event loop
using libcurl's multi-socket API. No threads, no busy-polling. A
selector-style event loop is required (on Windows install
``WindowsSelectorEventLoopPolicy``).

Example::

    async with pycurl.AsyncCurlMulti() as multi:
        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, "https://example.com")
        await multi.perform(curl)
        print(curl.getinfo(pycurl.RESPONSE_CODE))
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Iterable

from pycurl._pycurl import (
    CSELECT_IN,
    CSELECT_OUT,
    Curl,
    CurlMulti,
    M_SOCKETFUNCTION,
    M_TIMERFUNCTION,
    POLL_IN,
    POLL_NONE,
    POLL_OUT,
    POLL_REMOVE,
    SOCKET_TIMEOUT,
    error as _pycurl_error,
)


@dataclass(slots=True)
class _SocketState:
    """Per-socket state attached via ``CurlMulti.assign``.

    Mutated in place: libcurl returns the same instance as ``socketp`` on
    every callback for a given socket, so ``assign`` is called once per
    socket.
    """

    read_registered: bool = False
    write_registered: bool = False


class AsyncCurlMulti:
    """AsyncCurlMulti(close_handles=False) -> AsyncCurlMulti object

    An asyncio-driven wrapper around :py:class:`pycurl.CurlMulti`. Each
    :py:class:`pycurl.Curl` transfer is represented by an
    :py:class:`asyncio.Future` that resolves to the same ``Curl`` object on
    success or raises :py:class:`pycurl.error` on failure.

    The constructor does not require a running event loop; the loop is
    captured on the first call to :py:meth:`add_handle` and the instance
    is bound to that loop for its lifetime.

    A selector-style asyncio event loop is required. On a non-selector
    loop (e.g., Windows ``ProactorEventLoop``) :py:meth:`add_handle`
    raises :py:exc:`RuntimeError` with guidance on switching policy.

    Always call :py:meth:`aclose` (or use ``async with``) to release the
    underlying multi handle promptly.

    *close_handles* is forwarded to :py:class:`pycurl.CurlMulti`. When
    ``True``, any easy handle still attached to the multi when
    :py:meth:`aclose` runs is also closed by libcurl.

    Example::

        async with pycurl.AsyncCurlMulti() as multi:
            curl = pycurl.Curl()
            curl.setopt(pycurl.URL, "https://example.com")
            await multi.perform(curl)
            print(curl.getinfo(pycurl.RESPONSE_CODE))

    Batch example::

        async with pycurl.AsyncCurlMulti() as multi:
            for url in urls:
                curl = pycurl.Curl()
                curl.setopt(pycurl.URL, url)
                multi.add_handle(curl)
            results = await asyncio.gather(*multi.futures())
    """

    def __init__(self, close_handles: bool = False) -> None:
        self._multi: CurlMulti = CurlMulti(close_handles=close_handles)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._futures: dict[Curl, asyncio.Future[Curl]] = {}
        self._assigned_fds: set[int] = set()
        self._timer: asyncio.Handle | None = None
        self._closing: bool = False
        self._multi.setopt(M_SOCKETFUNCTION, self._on_socket)
        self._multi.setopt(M_TIMERFUNCTION, self._on_timer)

    def setopt(self, option: int, value: Any) -> None:
        """setopt(option, value) -> None

        Sets a multi-handle option. Equivalent to
        :py:meth:`pycurl.CurlMulti.setopt`, except that
        ``M_SOCKETFUNCTION`` and ``M_TIMERFUNCTION`` are owned by
        ``AsyncCurlMulti`` and raise :py:exc:`ValueError` if set externally.

        *option* is a ``pycurl.M_*`` constant identifying which option to
        set. *value* is the new option value; different options accept
        values of different types (see :py:meth:`pycurl.CurlMulti.setopt`).
        """
        if option in (M_SOCKETFUNCTION, M_TIMERFUNCTION):
            raise ValueError("AsyncCurlMulti owns M_SOCKETFUNCTION/M_TIMERFUNCTION")
        self._multi.setopt(option, value)

    def add_handle(self, curl: Curl) -> asyncio.Future[Curl]:
        """add_handle(curl) -> asyncio.Future

        Schedules *curl* for transfer and returns an
        :py:class:`asyncio.Future` that resolves to *curl* on success or
        raises :py:class:`pycurl.error` on failure. Cancelling the future
        removes the handle; cleanup runs on the next event-loop tick.

        *curl* is a :py:class:`pycurl.Curl` easy handle.

        The first call captures the running event loop and binds this
        instance to it. Raises :py:exc:`RuntimeError` if called outside
        a running loop, after :py:meth:`aclose`, or if *curl* is already
        registered.
        """
        if self.closed():
            raise RuntimeError("AsyncCurlMulti is closed")
        if curl in self._futures:
            raise RuntimeError("Curl handle is already registered")
        loop = self._ensure_loop()
        fut: asyncio.Future[Curl] = loop.create_future()
        self._futures[curl] = fut
        # Bind curl into the done-callback so cancellation can find the
        # right handle without a reverse-lookup map.
        fut.add_done_callback(partial(self._on_future_done, curl))
        try:
            self._multi.add_handle(curl)
        except Exception:
            # Roll back bookkeeping; the unreachable future GCs cleanly.
            self._futures.pop(curl, None)
            raise
        return fut

    def remove_handle(self, curl: Curl) -> None:
        """remove_handle(curl) -> None

        Removes *curl* from this multi handle and cancels its future
        (if not already done). Synchronous; if you need to observe the
        cancellation propagate, await the future returned from the
        original :py:meth:`add_handle` call.

        *curl* is a :py:class:`pycurl.Curl` easy handle. Raises
        :py:exc:`RuntimeError` if *curl* is not registered or after
        :py:meth:`aclose`. Raises :py:class:`pycurl.error` if libcurl
        rejects the removal.
        """
        if self.closed():
            raise RuntimeError("AsyncCurlMulti is closed")
        fut = self._futures.pop(curl, None)
        if fut is None:
            raise RuntimeError("Curl handle is not registered")
        self._multi.remove_handle(curl)
        if not fut.done():
            fut.cancel()

    async def perform(self, curl: Curl) -> Curl:
        """perform(curl) -> Curl object

        Coroutine equivalent to ``await self.add_handle(curl)``. Schedules
        *curl* for transfer and returns it once the transfer completes.
        Raises :py:class:`pycurl.error` on failure.

        *curl* is a :py:class:`pycurl.Curl` easy handle.
        """
        return await self.add_handle(curl)

    def futures(
        self,
        curls: Iterable[Curl] | None = None,
    ) -> tuple[asyncio.Future[Curl], ...]:
        """futures(curls=None) -> tuple of asyncio.Future

        Returns a snapshot of futures for transfers currently registered
        with this multi handle.

        *curls* is either ``None`` (the default) or an iterable of
        :py:class:`pycurl.Curl` easy handles. When ``None``, the result
        contains every pending future in the order in which the handles
        were added via :py:meth:`add_handle`. When an iterable is given,
        the result contains the corresponding futures in input order and
        length (so duplicates yield duplicate references to the same
        future).

        Completed or cancelled transfers are not included in later
        snapshots.

        Raises :py:exc:`KeyError` if any handle in *curls* is not
        currently registered.
        """
        if curls is None:
            return tuple(self._futures.values())
        out: list[asyncio.Future[Curl]] = []
        for curl in curls:
            try:
                out.append(self._futures[curl])
            except KeyError:
                raise KeyError(curl) from None
        return tuple(out)

    def closed(self) -> bool:
        """closed() -> bool

        Returns ``True`` if the underlying :py:class:`pycurl.CurlMulti`
        handle has been closed.
        """
        return self._multi.closed()

    async def aclose(self) -> None:
        """aclose() -> None

        Coroutine. Cancels the pending timer, removes all in-flight
        handles, unregisters socket watchers, and closes the underlying
        multi handle. Pending futures are cancelled. Idempotent.
        """
        if self.closed():
            return
        self._cancel_timer()
        # remove_handle fires POLL_REMOVE, which unregisters watchers and unassigns.
        for curl, fut in list(self._futures.items()):
            self._futures.pop(curl, None)
            try:
                self._multi.remove_handle(curl)
            except _pycurl_error:
                pass
            if not fut.done():
                fut.cancel()
        # Defensive: clean up any fds libcurl did not fire POLL_REMOVE for.
        if self._loop is not None:
            for fd in list(self._assigned_fds):
                try:
                    self._loop.remove_reader(fd)
                except (NotImplementedError, ValueError, OSError):
                    pass
                try:
                    self._loop.remove_writer(fd)
                except (NotImplementedError, ValueError, OSError):
                    pass
                try:
                    self._multi.unassign(fd)
                except _pycurl_error:
                    pass
            self._assigned_fds.clear()
        self._closing = True
        try:
            self._multi.close()
        finally:
            self._closing = False

    async def __aenter__(self) -> AsyncCurlMulti:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> None:
        await self.aclose()

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        import asyncio

        loop = asyncio.get_running_loop()
        if self._loop is None:
            proactor = getattr(asyncio, "ProactorEventLoop", None)
            if proactor is not None and isinstance(loop, proactor):
                raise RuntimeError(
                    "AsyncCurlMulti requires a selector-style event loop"
                )
            self._loop = loop
        elif self._loop is not loop:
            raise RuntimeError("AsyncCurlMulti is bound to a different event loop")
        return loop

    def _on_socket(
        self,
        what: int,
        fd: int,
        multi: CurlMulti,
        socketp: _SocketState | None,
    ) -> None:
        if what == POLL_REMOVE:
            if socketp is not None:
                self._unregister_fd(fd, socketp)
            else:
                self._assigned_fds.discard(fd)
            return

        if what == POLL_NONE:
            # No current interest; drop watchers but keep the assignment so
            # the next POLL_IN/OUT lands with the same socketp.
            if socketp is not None:
                self._unregister_watchers(fd, socketp)
            return

        # POLL_IN/OUT/INOUT below: do not register new watchers if the multi
        # is being torn down.
        if self._closing:
            return

        if socketp is None:
            state = _SocketState()
            first_observation = True
            self._assigned_fds.add(fd)
        else:
            state = socketp
            first_observation = False

        want_read = bool(what & POLL_IN)
        want_write = bool(what & POLL_OUT)

        assert self._loop is not None, "callback fired before _ensure_loop"
        if want_read and not state.read_registered:
            self._loop.add_reader(fd, self._on_readable, fd, state)
        elif not want_read and state.read_registered:
            self._loop.remove_reader(fd)

        if want_write and not state.write_registered:
            self._loop.add_writer(fd, self._on_writable, fd, state)
        elif not want_write and state.write_registered:
            self._loop.remove_writer(fd)

        state.read_registered = want_read
        state.write_registered = want_write
        if first_observation:
            multi.assign(fd, state)

    def _unregister_watchers(self, fd: int, state: _SocketState) -> None:
        assert self._loop is not None, "callback fired before _ensure_loop"
        if state.read_registered:
            self._loop.remove_reader(fd)
            state.read_registered = False
        if state.write_registered:
            self._loop.remove_writer(fd)
            state.write_registered = False

    def _unregister_fd(self, fd: int, state: _SocketState) -> None:
        self._unregister_watchers(fd, state)
        try:
            self._multi.unassign(fd)
        except _pycurl_error:
            pass
        self._assigned_fds.discard(fd)

    def _on_timer(self, timeout_ms: int) -> None:
        if self._closing:
            return
        self._schedule_timer(timeout_ms)

    def _schedule_timer(self, timeout_ms: int) -> None:
        self._cancel_timer()
        if timeout_ms < 0:
            return
        assert self._loop is not None, "callback fired before _ensure_loop"
        if timeout_ms == 0:
            # call_soon defers past the current libcurl call to avoid re-entry.
            self._timer = self._loop.call_soon(self._fire_timeout)
        else:
            self._timer = self._loop.call_later(timeout_ms / 1000.0, self._fire_timeout)

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _on_readable(self, fd: int, state: _SocketState) -> None:
        if not state.read_registered:
            return
        self._drive(fd, CSELECT_IN)

    def _on_writable(self, fd: int, state: _SocketState) -> None:
        if not state.write_registered:
            return
        self._drive(fd, CSELECT_OUT)

    def _fire_timeout(self) -> None:
        self._timer = None
        self._drive(SOCKET_TIMEOUT, 0)

    def _drive(self, fd: int, mask: int) -> None:
        if self._closing:
            return
        try:
            self._multi.socket_action(fd, mask)
        except _pycurl_error as exc:
            # Multi is in a bad state; info_read will not produce completions.
            self._fail_all_pending(exc)
            return
        self._drain()

    def _fail_all_pending(self, exc: BaseException) -> None:
        for curl in list(self._futures):
            self._resolve(curl, exc)

    def _drain(self) -> None:
        _, ok, err = self._multi.info_read()
        for curl in ok:
            self._resolve(curl, None)
        for curl, code, msg in err:
            self._resolve(curl, _pycurl_error(code, msg))

    def _resolve(self, curl: Curl, exc: BaseException | None) -> None:
        fut = self._futures.pop(curl, None)
        if fut is None:
            return
        try:
            self._multi.remove_handle(curl)
        except _pycurl_error:
            pass
        if fut.done():
            return
        if exc is None:
            fut.set_result(curl)
        else:
            fut.set_exception(exc)

    def _on_future_done(self, curl: Curl, _future: asyncio.Future[Curl]) -> None:
        # No-op if aclose() or _resolve already cleaned up.
        if self._closing or curl not in self._futures:
            return
        self._futures.pop(curl, None)
        try:
            self._multi.remove_handle(curl)
        except _pycurl_error:
            pass
