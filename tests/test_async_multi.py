from __future__ import annotations

import asyncio
import contextlib
import sys
from collections.abc import Callable, Coroutine, Iterator
from io import BytesIO
from typing import Any
from unittest import mock

import pycurl
import pytest


def _run(coro: Coroutine[Any, Any, None]) -> None:
    # AsyncCurlMulti requires a selector-style loop; Windows defaults to
    # ProactorEventLoop, which does not implement add_reader/add_writer.
    if sys.platform == "win32":
        loop = asyncio.SelectorEventLoop()
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()
    else:
        asyncio.run(coro)


def _easy(url: str) -> tuple[pycurl.Curl, BytesIO]:
    curl = pycurl.Curl()
    curl.setopt(pycurl.URL, url)
    buf = BytesIO()
    curl.setopt(pycurl.WRITEDATA, buf)
    return curl, buf


class _StubMulti:
    """Whitebox stand-in for ``CurlMulti`` that records assign/unassign calls."""

    def __init__(self) -> None:
        self.assigned: list[Any] = []
        self.unassigned: list[int] = []

    def assign(self, _fd: int, state: Any) -> None:
        self.assigned.append(state)

    def unassign(self, fd: int) -> None:
        self.unassigned.append(fd)

    @property
    def closed(self) -> bool:
        return False


@contextlib.contextmanager
def _stubbed_socket_io(
    multi: pycurl.AsyncCurlMulti,
) -> Iterator[tuple[_StubMulti, list[tuple[str, int]]]]:
    """Replace ``multi._multi`` with a stub and patch the loop's fd watchers.

    Yields ``(stub, calls)``. Tests read ``stub.assigned`` /
    ``stub.unassigned`` for libcurl-side capture and ``calls`` for the
    asyncio watcher sequence. Restores the real multi on exit.
    """
    loop = asyncio.get_running_loop()
    multi._loop = loop
    calls: list[tuple[str, int]] = []

    def _record(name: str) -> Callable[..., None]:
        def fn(fd: int, *_a: object, **_kw: object) -> None:
            calls.append((name, fd))

        return fn

    real_multi = multi._multi
    stub = _StubMulti()
    multi._multi = stub  # type: ignore[assignment]
    try:
        with (
            mock.patch.object(loop, "add_reader", side_effect=_record("add_reader")),
            mock.patch.object(
                loop, "remove_reader", side_effect=_record("remove_reader")
            ),
            mock.patch.object(loop, "add_writer", side_effect=_record("add_writer")),
            mock.patch.object(
                loop, "remove_writer", side_effect=_record("remove_writer")
            ),
        ):
            yield stub, calls
    finally:
        multi._multi = real_multi


def test_basic_get(app: str) -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            curl, buf = _easy(f"{app}/success")
            try:
                result = await multi.perform(curl)
                assert result is curl
                assert curl.getinfo(pycurl.RESPONSE_CODE) == 200
                assert buf.getvalue() == b"success"
            finally:
                curl.close()

    _run(main())


def test_concurrent_handles(app: str) -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            handles = [_easy(f"{app}/success") for _ in range(3)]
            try:
                results = await asyncio.gather(*[multi.perform(c) for c, _ in handles])
                assert len(results) == 3
                for c, buf in handles:
                    assert c.getinfo(pycurl.RESPONSE_CODE) == 200
                    assert buf.getvalue() == b"success"
            finally:
                for c, _ in handles:
                    c.close()

    _run(main())


def test_http_error_status_does_not_fail_future(app: str) -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            curl, _ = _easy(f"{app}/status/404")
            try:
                result = await multi.perform(curl)
                assert result is curl
                assert curl.getinfo(pycurl.RESPONSE_CODE) == 404
            finally:
                curl.close()

    _run(main())


def test_failure_surfaces_exception() -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            curl = pycurl.Curl()
            # 127.0.0.1:1 is reserved and refused fast — avoids DNS / long timeouts.
            curl.setopt(pycurl.URL, "http://127.0.0.1:1/")
            curl.setopt(pycurl.CONNECTTIMEOUT, 2)
            curl.setopt(pycurl.WRITEDATA, BytesIO())
            try:
                with pytest.raises(pycurl.error):
                    await multi.perform(curl)
            finally:
                curl.close()

    _run(main())


def test_timer_path_drives_completion(app: str) -> None:
    async def main() -> None:
        loop = asyncio.get_running_loop()
        original = loop.call_soon
        timer_calls = 0

        def counting_call_soon(
            cb: Callable[..., None], *args: object, context: Any = None
        ) -> asyncio.Handle:
            nonlocal timer_calls
            if getattr(cb, "__name__", "") == "_fire_timeout":
                timer_calls += 1
            return original(cb, *args, context=context)

        with mock.patch.object(loop, "call_soon", side_effect=counting_call_soon):
            async with pycurl.AsyncCurlMulti() as multi:
                curl, _ = _easy(f"{app}/success")
                try:
                    await multi.perform(curl)
                finally:
                    curl.close()

        assert timer_calls >= 1

    _run(main())


def test_cancellation_cleans_up(app: str) -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            curl, _ = _easy(f"{app}/long_pause")
            try:
                fut = multi.add_handle(curl)
                for _ in range(5):
                    await asyncio.sleep(0.01)
                fut.cancel()
                for _ in range(5):
                    await asyncio.sleep(0.01)
                assert curl not in multi._futures
                assert multi._assigned_fds == set()
            finally:
                curl.close()

    _run(main())


def test_cancelled_future_not_resolved_by_drain(app: str) -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            curl, _ = _easy(f"{app}/short_wait?delay=0.1")
            try:
                fut = multi.add_handle(curl)
                await asyncio.sleep(0.01)
                fut.cancel()
                # Long enough for /short_wait to finish; any drain in that
                # window must not re-resolve fut.
                await asyncio.sleep(0.3)
                assert fut.cancelled()
                assert curl not in multi._futures
            finally:
                curl.close()

    _run(main())


def test_close_idempotent() -> None:
    async def main() -> None:
        multi = pycurl.AsyncCurlMulti()
        await multi.aclose()
        await multi.aclose()
        assert multi.closed is True

    _run(main())


def test_close_cancels_pending(app: str) -> None:
    async def main() -> None:
        multi = pycurl.AsyncCurlMulti()
        curl, _ = _easy(f"{app}/long_pause")
        try:
            fut = multi.add_handle(curl)
            await asyncio.sleep(0.01)
            await multi.aclose()
            assert fut.cancelled() or fut.done()
            assert multi._futures == {}
            assert multi._assigned_fds == set()
        finally:
            curl.close()

    _run(main())


def test_setopt_blocks_socket_timer_function() -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            with pytest.raises(ValueError):
                multi.setopt(pycurl.M_SOCKETFUNCTION, lambda *_: None)
            with pytest.raises(ValueError):
                multi.setopt(pycurl.M_TIMERFUNCTION, lambda *_: None)
            multi.setopt(pycurl.M_MAX_HOST_CONNECTIONS, 4)

    _run(main())


def test_duplicate_add_handle_rejected(app: str) -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            curl, _ = _easy(f"{app}/success")
            try:
                fut = multi.add_handle(curl)
                with pytest.raises(RuntimeError):
                    multi.add_handle(curl)
                assert curl in multi._futures
                await fut
                assert curl.getinfo(pycurl.RESPONSE_CODE) == 200
            finally:
                curl.close()

    _run(main())


def test_remove_handle_cancels_future(app: str) -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            curl, _ = _easy(f"{app}/long_pause")
            try:
                fut = multi.add_handle(curl)
                await asyncio.sleep(0.01)
                multi.remove_handle(curl)
                assert curl not in multi._futures
                assert fut.cancelled()
                # Flush the deferred done-callback; it should be a no-op.
                await asyncio.sleep(0)
                assert curl not in multi._futures
                assert fut.cancelled()
            finally:
                curl.close()

    _run(main())


def test_remove_handle_unregistered_raises() -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            stranger = pycurl.Curl()
            try:
                with pytest.raises(RuntimeError, match="not registered"):
                    multi.remove_handle(stranger)
            finally:
                stranger.close()

    _run(main())


def test_remove_handle_after_close_raises() -> None:
    async def main() -> None:
        multi = pycurl.AsyncCurlMulti()
        curl = pycurl.Curl()
        try:
            await multi.aclose()
            with pytest.raises(RuntimeError, match="closed"):
                multi.remove_handle(curl)
        finally:
            curl.close()

    _run(main())


def test_gather_with_sibling_failure(app: str) -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            ok_curl, ok_buf = _easy(f"{app}/success")
            bad_curl = pycurl.Curl()
            bad_curl.setopt(pycurl.URL, "http://127.0.0.1:1/")
            bad_curl.setopt(pycurl.CONNECTTIMEOUT, 2)
            bad_curl.setopt(pycurl.WRITEDATA, BytesIO())
            try:
                results = await asyncio.gather(
                    multi.perform(ok_curl),
                    multi.perform(bad_curl),
                    return_exceptions=True,
                )
                assert results[0] is ok_curl
                assert ok_curl.getinfo(pycurl.RESPONSE_CODE) == 200
                assert ok_buf.getvalue() == b"success"
                assert isinstance(results[1], pycurl.error)
                assert multi._futures == {}
                assert multi._assigned_fds == set()
            finally:
                ok_curl.close()
                bad_curl.close()

    _run(main())


def test_socket_action_failure_fails_pending_futures() -> None:
    async def main() -> None:
        multi = pycurl.AsyncCurlMulti()
        try:
            loop = asyncio.get_running_loop()
            multi._loop = loop

            fake_curl = object()
            fut: asyncio.Future = loop.create_future()
            multi._futures[fake_curl] = fut  # type: ignore[index]

            injected = pycurl.error(7, "injected socket_action failure")
            real_multi = multi._multi

            class _RaisingMulti:
                def socket_action(self, fd: int, mask: int) -> None:
                    raise injected

                def remove_handle(self, curl: object) -> None:
                    pass

                def info_read(self, *_a: object) -> tuple[int, list, list]:
                    return (0, [], [])

                @property
                def closed(self) -> bool:
                    return False

            multi._multi = _RaisingMulti()  # type: ignore[assignment]
            try:
                multi._fire_timeout()
            finally:
                multi._multi = real_multi

            assert fut.done()
            with pytest.raises(pycurl.error) as excinfo:
                await fut
            assert excinfo.value is injected
            assert fake_curl not in multi._futures  # type: ignore[comparison-overlap]
        finally:
            await multi.aclose()

    _run(main())


def test_back_to_back_add_handle(app: str) -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            handles = [_easy(f"{app}/success") for _ in range(5)]
            try:
                futs = [multi.add_handle(c) for c, _ in handles]
                results = await asyncio.gather(*futs)
                assert len(results) == 5
                for c, buf in handles:
                    assert c.getinfo(pycurl.RESPONSE_CODE) == 200
                    assert buf.getvalue() == b"success"
            finally:
                for c, _ in handles:
                    c.close()

    _run(main())


def test_socket_mask_transitions() -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            with _stubbed_socket_io(multi) as (stub, calls):
                fd = 99
                multi._on_socket(pycurl.POLL_IN, fd, stub, None)
                state = stub.assigned[-1]
                multi._on_socket(pycurl.POLL_INOUT, fd, stub, state)
                multi._on_socket(pycurl.POLL_OUT, fd, stub, state)
                multi._on_socket(pycurl.POLL_REMOVE, fd, stub, state)

            assert calls == [
                ("add_reader", fd),
                ("add_writer", fd),
                ("remove_reader", fd),
                ("remove_writer", fd),
            ]
            assert len(stub.assigned) == 1

    _run(main())


def test_add_handle_rollback_on_failure(app: str) -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            curl, _ = _easy(f"{app}/success")
            try:
                multi._loop = asyncio.get_running_loop()
                injected = pycurl.error(2, "injected add_handle failure")
                real_add = multi._multi.add_handle

                class _RaisingMulti:
                    def add_handle(self, _curl: object) -> None:
                        raise injected

                    def __getattr__(self, name: str) -> object:
                        return getattr(real_add.__self__, name)

                multi._multi = _RaisingMulti()  # type: ignore[assignment]
                try:
                    with pytest.raises(pycurl.error) as excinfo:
                        multi.add_handle(curl)
                    assert excinfo.value is injected
                finally:
                    multi._multi = real_add.__self__  # type: ignore[assignment]

                assert multi._futures == {}
            finally:
                curl.close()

    _run(main())


def test_poll_inout_then_remove_clears_both_watchers() -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            with _stubbed_socket_io(multi) as (stub, calls):
                fd = 77
                multi._on_socket(pycurl.POLL_INOUT, fd, stub, None)
                state = stub.assigned[-1]
                multi._on_socket(pycurl.POLL_REMOVE, fd, stub, state)

            assert calls == [
                ("add_reader", fd),
                ("add_writer", fd),
                ("remove_reader", fd),
                ("remove_writer", fd),
            ]
            assert fd not in multi._assigned_fds

    _run(main())


def test_poll_none_keeps_assignment() -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            with _stubbed_socket_io(multi) as (stub, calls):
                fd = 88
                multi._on_socket(pycurl.POLL_INOUT, fd, stub, None)
                state = stub.assigned[-1]
                multi._on_socket(pycurl.POLL_NONE, fd, stub, state)

            assert ("remove_reader", fd) in calls
            assert ("remove_writer", fd) in calls
            # No unassign; fd still tracked; state flags cleared for re-register.
            assert stub.unassigned == []
            assert fd in multi._assigned_fds
            assert state.read_registered is False  # type: ignore[attr-defined]
            assert state.write_registered is False  # type: ignore[attr-defined]

    _run(main())


def test_negative_timer_clears_pending_handle() -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            multi._loop = asyncio.get_running_loop()
            multi._on_timer(50)
            assert multi._timer is not None
            multi._on_timer(-1)
            assert multi._timer is None

    _run(main())


def test_ensure_loop_rejects_different_loop() -> None:
    multi = pycurl.AsyncCurlMulti()
    try:

        async def bind() -> None:
            multi._ensure_loop()

        _run(bind())  # binds to the first loop, which then closes

        async def reuse() -> None:
            with pytest.raises(RuntimeError, match="different event loop"):
                multi._ensure_loop()

        _run(reuse())
    finally:
        _run(multi.aclose())


def test_proactor_loop_raises_clear_error() -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            # On non-Windows ProactorEventLoop is absent; patch it to the
            # running loop's class so the isinstance check fires.
            loop_class = asyncio.get_running_loop().__class__
            with mock.patch.object(
                asyncio, "ProactorEventLoop", loop_class, create=True
            ):
                with pytest.raises(RuntimeError, match="selector-style event loop"):
                    multi._ensure_loop()

    _run(main())


def test_stale_watcher_callback_skipped() -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            state = pycurl.async_multi._SocketState()
            with mock.patch.object(multi, "_drive") as drive:
                multi._on_readable(99, state)
                multi._on_writable(99, state)
            drive.assert_not_called()

    _run(main())


def test_on_timer_noop_during_close() -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            multi._loop = asyncio.get_running_loop()
            multi._closing = True
            multi._on_timer(50)
            assert multi._timer is None

    _run(main())


def test_close_time_poll_in_is_ignored() -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            with _stubbed_socket_io(multi) as (stub, calls):
                multi._closing = True
                multi._on_socket(pycurl.POLL_IN, 99, stub, None)
            assert calls == []
            assert stub.assigned == []
            assert 99 not in multi._assigned_fds

    _run(main())


def test_assign_used_for_socket_state(app: str) -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            curl = pycurl.Curl()
            curl.setopt(pycurl.URL, f"{app}/success")

            in_flight_assigned: set[int] = set()

            def write_cb(data: bytes) -> int:
                if not in_flight_assigned:
                    in_flight_assigned.update(multi._assigned_fds)
                return len(data)

            curl.setopt(pycurl.WRITEFUNCTION, write_cb)
            try:
                await multi.perform(curl)
                assert in_flight_assigned
                assert multi._assigned_fds == set()
            finally:
                curl.close()

    _run(main())


def test_futures_empty_on_fresh_multi() -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            assert multi.futures() == ()

    _run(main())


def test_futures_returns_pending_in_insertion_order(app: str) -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            handles = [_easy(f"{app}/long_pause") for _ in range(3)]
            try:
                expected = [multi.add_handle(c) for c, _ in handles]
                got = multi.futures()
                assert got == tuple(expected)
                assert all(not f.done() for f in got)
            finally:
                for f in expected:
                    f.cancel()
                for c, _ in handles:
                    c.close()

    _run(main())


def test_futures_subset_preserves_input_order(app: str) -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            handles = [_easy(f"{app}/long_pause") for _ in range(3)]
            try:
                futs = [multi.add_handle(c) for c, _ in handles]
                c0, c1, c2 = (h[0] for h in handles)
                got = multi.futures([c2, c0])
                assert got == (futs[2], futs[0])
            finally:
                for f in futs:
                    f.cancel()
                for c, _ in handles:
                    c.close()

    _run(main())


def test_futures_unknown_handle_raises_keyerror() -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            stranger = pycurl.Curl()
            try:
                with pytest.raises(KeyError) as excinfo:
                    multi.futures([stranger])
                assert excinfo.value.args[0] is stranger
            finally:
                stranger.close()

    _run(main())


def test_futures_duplicate_handle_returns_duplicate(app: str) -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            curl, _ = _easy(f"{app}/long_pause")
            try:
                fut = multi.add_handle(curl)
                got = multi.futures([curl, curl])
                assert got == (fut, fut)
                assert got[0] is got[1]
            finally:
                fut.cancel()
                curl.close()

    _run(main())


def test_futures_excludes_completed_transfers(app: str) -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            curl, _ = _easy(f"{app}/success")
            try:
                await multi.perform(curl)
                assert curl not in multi.futures()
                assert multi.futures() == ()
            finally:
                curl.close()

    _run(main())


def test_futures_compose_with_gather(app: str) -> None:
    async def main() -> None:
        async with pycurl.AsyncCurlMulti() as multi:
            handles = [_easy(f"{app}/success") for _ in range(4)]
            try:
                for c, _ in handles:
                    multi.add_handle(c)
                results = await asyncio.gather(*multi.futures())
                assert len(results) == 4
                for c, _ in handles:
                    assert c.getinfo(pycurl.RESPONSE_CODE) == 200
            finally:
                for c, _ in handles:
                    c.close()

    _run(main())
