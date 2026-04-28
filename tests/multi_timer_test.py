from io import BytesIO

import pycurl

from . import util


def _make_easy(app):
    c = util.DefaultCurl()
    c.body = BytesIO()
    c.setopt(c.URL, f"{app}/success")
    c.setopt(c.WRITEFUNCTION, c.body.write)
    return c


def test_multi_timer_perform_loop(app):
    timers: list[int] = []

    def timer(timeout_ms):
        timers.append(timeout_ms)

    multi = pycurl.CurlMulti()
    multi.setopt(pycurl.M_TIMERFUNCTION, timer)

    handles = [_make_easy(app) for _ in range(3)]
    for c in handles:
        multi.add_handle(c)

    try:
        num_handles = len(handles)
        while num_handles:
            _, num_handles = multi.perform()
            multi.select(1.0)

        for c in handles:
            assert c.body.getvalue().decode() == "success"
            assert c.getinfo(c.HTTP_CODE) == 200
    finally:
        for c in handles:
            multi.remove_handle(c)
            c.close()
        multi.close()

    assert timers, "expected at least one timer callback"
    # libcurl 7.23.0 produces a 0 timer; older versions may negative-init.
    assert timers[0] >= 0
