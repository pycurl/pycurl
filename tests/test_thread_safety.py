from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import pycurl
import pytest

from . import util


HAS_XFERINFOFUNCTION = hasattr(pycurl, "XFERINFOFUNCTION")


def _run_workers(worker, n_workers):
    with ThreadPoolExecutor(max_workers=n_workers) as ex:
        futures = [ex.submit(worker) for _ in range(n_workers)]
        return [f.result() for f in futures]


def _drive_multi(m):
    _, num_handles = m.perform()
    while num_handles:
        m.select(0.1)
        _, num_handles = m.perform()
    while True:
        queued, _, err = m.info_read()
        if err:
            pytest.fail(f"Multi transfer errors: {err}")
        if not queued:
            break


@pytest.mark.parallel_threads(4)
@pytest.mark.timeout(120)
def test_independent_curl_objects_in_parallel(app):
    c = util.DefaultCurl()
    for _ in range(5):
        buf = BytesIO()
        c.setopt(pycurl.URL, app + "/success")
        c.setopt(pycurl.WRITEFUNCTION, buf.write)
        c.perform()
        assert buf.getvalue() == b"success"


@pytest.mark.timeout(120)
def test_same_curl_with_user_lock(app):
    c = util.DefaultCurl()
    lock = threading.Lock()
    n_workers = 4
    iters_per_worker = 5
    # Barrier aligns worker start so the lock is contended on free-threaded builds.
    barrier = threading.Barrier(n_workers)
    results: list[bytes] = []

    def worker():
        barrier.wait()
        for _ in range(iters_per_worker):
            with lock:
                buf = BytesIO()
                c.setopt(pycurl.URL, app + "/success")
                c.setopt(pycurl.WRITEFUNCTION, buf.write)
                c.perform()
                results.append(buf.getvalue())

    _run_workers(worker, n_workers)

    assert results == [b"success"] * (n_workers * iters_per_worker)


@pytest.mark.parallel_threads(4)
@pytest.mark.timeout(120)
def test_independent_curlmulti_objects_in_parallel(app):
    n_easies = 3
    m = pycurl.CurlMulti()
    easies = []
    for _ in range(n_easies):
        c = util.DefaultCurl()
        buf = BytesIO()
        c.setopt(pycurl.URL, app + "/success")
        c.setopt(pycurl.WRITEFUNCTION, buf.write)
        m.add_handle(c)
        easies.append((c, buf))

    _drive_multi(m)

    assert [buf.getvalue() for _, buf in easies] == [b"success"] * n_easies


@pytest.mark.timeout(120)
def test_shared_curlmulti_with_user_lock(app):
    m = pycurl.CurlMulti()
    lock = threading.Lock()
    n_workers = 2
    iters_per_worker = 3
    results: list[bytes] = []

    def worker():
        for _ in range(iters_per_worker):
            c = util.DefaultCurl()
            buf = BytesIO()
            c.setopt(pycurl.URL, app + "/success")
            c.setopt(pycurl.WRITEFUNCTION, buf.write)

            with lock:
                m.add_handle(c)
                _drive_multi(m)
                m.remove_handle(c)

            results.append(buf.getvalue())

    _run_workers(worker, n_workers)

    assert results == [b"success"] * (n_workers * iters_per_worker)


@pytest.mark.parallel_threads(4)
@pytest.mark.timeout(120)
def test_callback_transfers_in_parallel(app):
    c = util.DefaultCurl()
    body = bytearray()
    headers: list[bytes] = []
    progress_called = False

    c.setopt(pycurl.URL, app + "/header?h=X-Test")
    c.setopt(pycurl.HTTPHEADER, ["X-Test: hello"])
    c.setopt(pycurl.WRITEFUNCTION, body.extend)
    c.setopt(pycurl.HEADERFUNCTION, headers.append)
    c.setopt(pycurl.NOPROGRESS, False)
    if HAS_XFERINFOFUNCTION:

        def progress(_dlt, _dln, _ult, _uln):
            nonlocal progress_called
            progress_called = True
            return 0

        c.setopt(pycurl.XFERINFOFUNCTION, progress)

    for _ in range(3):
        body.clear()
        headers.clear()
        progress_called = False
        c.perform()
        assert body == b"hello"
        assert any(h.lower().startswith(b"content-length") for h in headers)
        if HAS_XFERINFOFUNCTION:
            assert progress_called


@pytest.mark.timeout(120)
def test_share_with_many_curls_in_parallel(app):
    s = pycurl.CurlShare()
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_DNS)
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_SSL_SESSION)

    n_workers = 6
    iters_per_worker = 4
    results: list[bytes] = []
    results_lock = threading.Lock()

    def worker():
        c = util.DefaultCurl()
        c.setopt(pycurl.SHARE, s)
        for _ in range(iters_per_worker):
            buf = BytesIO()
            c.setopt(pycurl.URL, app + "/success")
            c.setopt(pycurl.WRITEFUNCTION, buf.write)
            c.perform()
            with results_lock:
                results.append(buf.getvalue())

    _run_workers(worker, n_workers)

    assert results == [b"success"] * (n_workers * iters_per_worker)
