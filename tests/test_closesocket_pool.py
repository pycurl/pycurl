import gc
import socket
import threading
import weakref
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import pycurl

from . import util

pytestmark = pytest.mark.skipif(
    util.pycurl_version_less_than(7, 21, 7), reason="libcurl < 7.21.7"
)


class KeepAliveHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


@pytest.fixture
def keepalive_server():
    servers = []

    def start():
        server = ThreadingHTTPServer(("127.0.0.1", 0), KeepAliveHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_port}/"

    yield start
    for server in servers:
        server.shutdown()
        server.server_close()


@pytest.fixture
def keepalive_url(keepalive_server):
    return keepalive_server()


def make_curl(url, closesocket, cls=pycurl.Curl):
    curl = cls()
    curl.setopt(pycurl.URL, url)
    curl.setopt(pycurl.WRITEFUNCTION, len)
    curl.setopt(pycurl.CLOSESOCKETFUNCTION, closesocket)
    return curl


def recorder(calls):
    def closesocket(curlfd):
        calls.append(curlfd)
        socket.close(curlfd)
        return 0

    return closesocket


def make_pool(kind, del_without_super=False):
    cls = pycurl.CurlMulti if kind == "multi" else pycurl.CurlShare
    if del_without_super:
        cls = type("Sub", (cls,), {"__del__": lambda self: None})
    pool = cls()
    if kind == "share":
        pool.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_CONNECT)
    return pool


def transfer(pool, curl):
    if isinstance(pool, pycurl.CurlMulti):
        pool.add_handle(curl)
        num_handles = 1
        while num_handles:
            _, num_handles = pool.perform()
            pool.select(1.0)
        pool.remove_handle(curl)
    else:
        curl.setopt(pycurl.SHARE, pool)
        curl.perform()


@pytest.mark.parametrize("pool_kind", ["multi", "share"])
def test_pool_outlives_easy(keepalive_url, pool_kind):
    calls = []
    closesocket = recorder(calls)
    ref = weakref.ref(closesocket)

    with make_pool(pool_kind) as pool:
        with make_curl(keepalive_url, closesocket) as curl:
            transfer(pool, curl)

        del curl, closesocket
        gc.collect()

        assert calls == [], "the connection is still pooled, nothing closed it yet"
        assert ref() is not None, "the pool must keep the callback alive"

    assert len(calls) == 1

    del pool
    gc.collect()
    assert ref() is None


@pytest.mark.parametrize("pool_kind", ["multi", "share"])
def test_clearing_pool_referents_keeps_owners_alive(keepalive_url, pool_kind):
    calls = []
    with make_pool(pool_kind) as pool:
        with make_curl(keepalive_url, recorder(calls)) as curl:
            transfer(pool, curl)
        for referent in gc.get_referents(pool):
            if isinstance(referent, (set, list)):
                referent.clear()

    assert len(calls) == 1


@pytest.mark.parametrize("pool_kind", ["multi", "share"])
def test_pool_cycle_through_the_callback_is_collectable(keepalive_url, pool_kind):
    pool = make_pool(pool_kind)

    def closesocket(curlfd, _pool=pool):
        socket.close(curlfd)
        return 0

    ref = weakref.ref(closesocket)
    with make_curl(keepalive_url, closesocket) as curl:
        transfer(pool, curl)

    del pool, closesocket
    gc.collect()
    assert ref() is None


@pytest.mark.parametrize("pool_kind", ["multi", "share"])
def test_pool_dealloc_skips_the_callback(keepalive_url, pool_kind):
    calls = []
    pool = make_pool(pool_kind, del_without_super=True)
    with make_curl(keepalive_url, recorder(calls)) as curl:
        transfer(pool, curl)

    del pool
    assert calls == []


@pytest.mark.parametrize("pool_kind", ["multi", "share"])
def test_failing_callback_does_not_silence_others(
    keepalive_server, unraisable, pool_kind
):
    calls = []

    def closesocket(curlfd):
        calls.append(curlfd)
        socket.close(curlfd)
        if len(calls) == 1:
            raise RuntimeError("first close fails")
        return 0

    with make_pool(pool_kind) as pool:
        for _ in range(2):
            with make_curl(keepalive_server(), closesocket) as curl:
                transfer(pool, curl)

    assert len(calls) == 2
    assert unraisable == [RuntimeError]


def test_standalone_easy_closes_its_pooled_connection(keepalive_url):
    calls = []
    closesocket = recorder(calls)
    ref = weakref.ref(closesocket)

    with make_curl(keepalive_url, closesocket) as curl:
        curl.perform()
        del closesocket

    assert len(calls) == 1

    del curl
    gc.collect()
    assert ref() is None


def test_duphandle_owners_are_independent(keepalive_url):
    inherited, replaced = [], []

    with make_curl(keepalive_url, recorder(inherited)) as parent:
        with parent.duphandle() as dup:
            parent.setopt(pycurl.CLOSESOCKETFUNCTION, recorder(replaced))
            dup.perform()
        assert len(inherited) == 1, "the clone must close through its own owner"
        assert replaced == []
        parent.perform()

    assert len(replaced) == 1
    assert len(inherited) == 1


@pytest.mark.parametrize("withdraw", ["unsetopt", "reset"])
def test_withdrawing_the_callback_silences_pooled_connections(keepalive_url, withdraw):
    calls = []
    with pycurl.CurlShare() as share:
        share.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_CONNECT)

        with make_curl(keepalive_url, recorder(calls)) as curl:
            curl.setopt(pycurl.SHARE, share)
            curl.perform()
            if withdraw == "unsetopt":
                curl.unsetopt(pycurl.CLOSESOCKETFUNCTION)
            else:
                curl.reset()

    assert calls == [], "the callback was withdrawn before the pool closed"


class SubCurl(pycurl.Curl):
    def __del__(self):
        # No super() call
        pass


def test_pooled_callback_runs_after_dealloc_teardown(keepalive_url):
    calls = []
    with pycurl.CurlShare() as share:
        share.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_CONNECT)

        curl = make_curl(keepalive_url, recorder(calls), SubCurl)
        curl.setopt(pycurl.SHARE, share)
        curl.perform()

        del curl
        assert calls == [], "the connection is still pooled, nothing closed it yet"

    assert len(calls) == 1, "the easy's teardown phase must not outlive the easy"


def test_owner_cycle_is_collectable(keepalive_url):
    curl = pycurl.Curl()

    def closesocket(curlfd, _curl=curl):
        return 0

    ref = weakref.ref(closesocket)
    curl.setopt(pycurl.URL, keepalive_url)
    curl.setopt(pycurl.WRITEFUNCTION, len)
    curl.setopt(pycurl.CLOSESOCKETFUNCTION, closesocket)
    curl.perform()

    del curl, closesocket
    gc.collect()
    assert ref() is None
