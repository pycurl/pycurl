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
def keepalive_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), KeepAliveHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/"
    server.shutdown()
    server.server_close()


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


@pytest.mark.parametrize("pool_kind", ["multi", "share"])
def test_pool_outlives_easy(keepalive_url, pool_kind):
    calls = []
    closesocket = recorder(calls)
    ref = weakref.ref(closesocket)

    if pool_kind == "multi":
        pool = pycurl.CurlMulti()
    else:
        pool = pycurl.CurlShare()
        pool.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_CONNECT)

    with pool:
        with make_curl(keepalive_url, closesocket) as curl:
            if pool_kind == "multi":
                pool.add_handle(curl)
                num_handles = 1
                while num_handles:
                    _, num_handles = pool.perform()
                    pool.select(1.0)
                pool.remove_handle(curl)
            else:
                curl.setopt(pycurl.SHARE, pool)
                curl.perform()

        del curl, closesocket
        gc.collect()

        assert calls == [], "the connection is still pooled, nothing closed it yet"
        assert ref() is not None, "the pool must keep the callback alive"

    assert len(calls) == 1

    del pool
    gc.collect()
    assert ref() is None


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
