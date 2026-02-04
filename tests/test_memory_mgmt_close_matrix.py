import gc
import logging
import weakref
import pytest
import pycurl

from . import util

logger = logging.getLogger(__name__)


def default_share() -> pycurl.CurlShare:
    s = pycurl.CurlShare(detach_on_close=False)
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_COOKIE)
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_DNS)
    s.setopt(pycurl.SH_SHARE, pycurl.LOCK_DATA_SSL_SESSION)
    return s


def gc_collect_hard(rounds: int = 3) -> None:
    for _ in range(rounds):
        gc.collect()


class Tracker:
    """
    Tracks python object liveness via weakref + optional gc.get_objects scan.
    """

    def __init__(self) -> None:
        self._items: list[tuple[str, weakref.ref, int]] = []

    def track(self, name: str, obj):
        r = weakref.ref(obj)
        self._items.append((name, r, id(obj)))
        return obj

    def assert_all_gone(self, *, also_check_gc_objects: bool = True) -> None:
        gc_collect_hard()

        # Only use gc.get_objects for live refs; ids can be reused after free.
        live_ids: set[int] | None = None
        if also_check_gc_objects:
            live_ids = {id(o) for o in gc.get_objects()}

        for name, r, obj_id in self._items:
            obj = r()
            if obj is None:
                continue

            tracked = (
                " (gc-tracked)" if live_ids is not None and obj_id in live_ids else ""
            )
            raise AssertionError(f"{name} still alive{tracked} (id={obj_id})")


@pytest.fixture(autouse=True)
def _gc_sanity():
    gc.set_debug(0)
    gc_collect_hard()
    yield
    gc.set_debug(0)
    gc_collect_hard()


@pytest.fixture
def make_multi():
    def _make(n=50, *, close_handles=False, url: str | None = None):
        m = pycurl.CurlMulti(close_handles=close_handles)
        easies = [util.DefaultCurl() for _ in range(n)]
        for e in easies:
            if url is not None:
                e.setopt(pycurl.URL, url)
                e.setopt(pycurl.CONNECTTIMEOUT, 5)
            m.add_handle(e)
        return m, easies

    return _make


@pytest.fixture
def make_share_easies():
    def _make(
        share: pycurl.CurlShare,
        n: int = 25,
        *,
        url: str | None = None,
        set_write: bool = True,
    ):
        easies: list[pycurl.Curl] = []
        sios: list[util.BytesIO] = []

        for _ in range(n):
            c = util.DefaultCurl()
            c.setopt(pycurl.SHARE, share)
            if url is not None:
                c.setopt(pycurl.URL, url)
                c.setopt(pycurl.CONNECTTIMEOUT, 5)
            if set_write:
                sio = util.BytesIO()
                c.setopt(pycurl.WRITEFUNCTION, sio.write)
                sios.append(sio)
            easies.append(c)

        return easies, sios

    return _make


def drive_multi_a_bit(multi: pycurl.CurlMulti, nb_handles: int) -> None:
    _, active = multi.perform()
    multi.select(0.25)
    _, active = multi.perform()
    assert 0 < active <= nb_handles
    queued, ok_list, err_list = multi.info_read()
    logger.info(
        "drive_multi_a_bit: active=%d queued=%d ok=%d err=%d",
        active,
        queued,
        len(ok_list),
        len(err_list),
    )
    assert queued >= 0
    assert len(ok_list) + len(err_list) <= nb_handles


def perform_all(easies: list[pycurl.Curl]) -> None:
    for c in easies:
        c.perform()


@pytest.mark.parametrize(
    "order",
    [
        "remove_then_close_easy",
        "close_easy_then_remove",
        "close_multi_then_drop",
        "del_multi_without_close",
        "close_multi_with_close_handles",
    ],
)
@pytest.mark.parametrize("phase", ["idle", "in_flight"])
def test_multi_close_matrix(app, make_multi, order, phase):
    tr = Tracker()

    url = f"{app}/long_pause"

    logger.info("test_close_matrix: order=%s phase=%s url=%s", order, phase, url)

    if order == "close_multi_with_close_handles":
        multi, easies = make_multi(n=50, close_handles=True, url=url)
    else:
        multi, easies = make_multi(n=50, close_handles=False, url=url)

    tr.track("multi", multi)
    for i, e in enumerate(easies):
        tr.track(f"easy[{i}]", e)

    if phase == "in_flight":
        drive_multi_a_bit(multi, len(easies))

    if order == "remove_then_close_easy":
        for e in easies:
            multi.remove_handle(e)
            e.close()

    elif order == "close_easy_then_remove":
        for e in easies:
            e.close()
            multi.remove_handle(e)

    elif order == "close_multi_then_drop":
        multi.close()

    elif order == "del_multi_without_close":
        pass

    elif order == "close_multi_with_close_handles":
        multi.close()

    else:
        raise AssertionError(f"unknown order: {order}")

    e = None
    del e
    del easies
    del multi

    tr.assert_all_gone()


def test_multi_close_and_remove_one_easy_gone_others_not(make_multi):
    multi, easies = make_multi(n=3, close_handles=False)

    victim = easies[1]
    survivors = [easies[0], easies[2]]

    victim_ref = weakref.ref(victim)
    survivor_refs = [weakref.ref(e) for e in survivors]

    victim.close()

    easies[1] = None
    victim = None
    gc_collect_hard()

    assert victim_ref() is None, "victim easy still alive (likely leaked strong ref)"

    for i, r in enumerate(survivor_refs):
        obj = r()
        assert obj is not None, f"survivor[{i}] unexpectedly collected"
        assert obj.closed() is False, f"survivor[{i}] unexpectedly closed"

    for e in survivors:
        multi.remove_handle(e)
        e.close()
    multi.close()

    e = None
    obj = None
    easies = None
    survivors = None
    multi = None
    gc_collect_hard()

    for i, r in enumerate(survivor_refs):
        assert r() is None, f"survivor[{i}] still alive after cleanup"


@pytest.mark.parametrize(
    "order",
    [
        # detach via easy close first, then close share
        "close_easies_then_close_share",
        # close share first, then close easies (should auto-detach)
        "close_share_then_perform_then_close_easies",
        # close share first, then just drop everything
        "close_share_then_drop",
        # detach explicitly (setopt SHARE=None), then close share
        "unsetopt_share_then_close_share",
        # drop share without close (exercise dealloc path)
        "del_share_without_close",
        # drop easies without close then close share (exercise GC finalizers)
        "del_easies_then_close_share",
    ],
)
def test_share_close_matrix(app, make_share_easies, order):
    tr = Tracker()
    s = default_share()
    tr.track("share", s)

    url = f"{app}/success"
    easies, sios = make_share_easies(s, n=40, url=url)
    for i, e in enumerate(easies):
        tr.track(f"easy[{i}]", e)

    e = None
    del e

    logger.info("test_share_close_matrix: order=%s n=%d", order, len(easies))

    if order == "close_easies_then_close_share":
        for e in easies:
            e.close()
            assert e.closed()
        s.close()
        assert s.closed()

    elif order == "close_share_then_perform_then_close_easies":
        with pytest.raises(pycurl.error):
            s.close()
        assert not s.closed()
        for e in easies:
            assert e.share() == s
        perform_all(easies)
        for e in easies:
            e.close()
            assert e.closed()

        for sio in sios:
            assert sio.getvalue().decode() == "success"

    elif order == "close_share_then_drop":
        with pytest.raises(pycurl.error):
            s.close()
        assert not s.closed()
        for e in easies:
            assert e.share() == s

    elif order == "unsetopt_share_then_close_share":
        for e in easies:
            e.setopt(pycurl.SHARE, None)
            assert e.share() is None
        s.close()
        assert s.closed()

    elif order == "del_share_without_close":
        pass

    elif order == "del_easies_then_close_share":
        for i in range(len(easies)):
            easies[i] = None
        gc_collect_hard()
        s.close()

    else:
        raise AssertionError(f"unknown order: {order}")

    e = None
    del e
    del sios
    del easies
    del s
    gc_collect_hard()

    tr.assert_all_gone()


def test_share_close_detaches_and_easy_still_succeeds(app, make_share_easies):
    s = default_share()
    easies, sios = make_share_easies(s, n=20, url=f"{app}/success")

    with pytest.raises(pycurl.error):
        s.close()
    assert not s.closed()

    for e in easies:
        assert e.share() == s

    for e in easies:
        e.unsetopt(pycurl.SHARE)
        assert e.share() is None

    perform_all(easies)

    for e in easies:
        e.close()

    for sio in sios:
        assert sio.getvalue().decode() == "success"


def test_share_close_one_easy_does_not_keep_share_or_others_alive(
    app, make_share_easies
):
    s = default_share()
    easies, _sios = make_share_easies(s, n=3, url=f"{app}/success", set_write=False)

    victim = easies[1]
    survivors = [easies[0], easies[2]]

    victim_ref = weakref.ref(victim)
    survivor_refs = [weakref.ref(e) for e in survivors]
    share_ref = weakref.ref(s)

    victim.close()
    easies[1] = None
    victim = None
    gc_collect_hard()

    assert victim_ref() is None, "victim easy still alive (likely leaked strong ref)"

    for i, r in enumerate(survivor_refs):
        obj = r()
        assert obj is not None, f"survivor[{i}] unexpectedly collected"
        assert obj.closed() is False, f"survivor[{i}] unexpectedly closed"

    for e in survivors:
        e.close()
    s.close()

    e = None
    r = None
    obj = None
    survivors = None
    easies = None
    s = None
    gc_collect_hard()

    assert share_ref() is None, "share still alive after cleanup"
    for i, r in enumerate(survivor_refs):
        assert r() is None, f"survivor[{i}] still alive after cleanup"
