import gc
import logging
import weakref
import pytest
import pycurl

from . import util

logger = logging.getLogger(__name__)


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

        for name, r, obj_id in self._items:
            assert r() is None, f"{name} still alive (id={obj_id})"

        if also_check_gc_objects:
            live_ids = {id(o) for o in gc.get_objects()}
            for name, _, obj_id in self._items:
                assert obj_id not in live_ids, (
                    f"{name} id still present in gc.get_objects() (id={obj_id})"
                )


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
def test_close_matrix(app, make_multi, order, phase):
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


def test_close_and_remove_one_easy_gone_others_not(make_multi):
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
