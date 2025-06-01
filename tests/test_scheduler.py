import pytest
import threading
from datetime import datetime, timedelta
from threading import Event

import scheduler


class FakeNotifyDate:
    def __init__(
        self, title: str, for_: str, should_return: bool, raise_exc: Exception = None
    ):
        """
        - title, for_ are just stored for logging/inspection
        - should_return controls what should_notify(...) returns
        - raise_exc, if not None, is raised when should_notify(...) is called
        """
        self.title = title
        self.for_ = for_
        self._should = should_return
        self._raise = raise_exc

    def should_notify(self, t: datetime) -> bool:
        if self._raise:
            raise self._raise
        return self._should


# ─────────────────────────────────────────────────────────────────────────────
# 2) A pytest fixture that monkey-patches the module-level notify()
#    so we can observe calls without performing HTTP.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def patch_notify(monkeypatch):
    """
    Replace scheduler.notify(nd) with a fake that simply records the nd.title
    in a list, so we can assert how many times or with what args it was called.
    """
    called = []

    def fake_notify(nd_instance):
        called.append(nd_instance.title)

    monkeypatch.setattr("scheduler.notify", fake_notify)
    return called


# ─────────────────────────────────────────────────────────────────────────────
# 3) Tests for _should_send()
# ─────────────────────────────────────────────────────────────────────────────


def test__should_send_returns_true_when_nd_should_notify(monkeypatch):
    # Arrange: A FakeNotifyDate whose should_notify returns True
    now = datetime.now()
    fake_nd = FakeNotifyDate(title="T1", for_="you", should_return=True)
    # We can pass any datetime, here `now`
    sched = scheduler.Scheduler.__new__(scheduler.Scheduler)
    # Manually set the attributes needed by _should_send:
    sched.notify_dates = []
    sched.fire_times = []
    sched.time_generator = iter([])  # unused for this test
    sched.stop_event = Event()
    sched.config_updated_event = Event()

    # Act & Assert:
    assert sched._should_send(fake_nd, now) is True


def test__should_send_catches_NotifyTimeAbsentError(monkeypatch):
    # Arrange: FakeNotifyDate that raises NotifyTimeAbsentError
    fake_nd = FakeNotifyDate(
        title="T2",
        for_="me",
        should_return=False,
        raise_exc=scheduler.NotifyTimeAbsentError(),
    )
    sched = scheduler.Scheduler.__new__(scheduler.Scheduler)
    sched.notify_dates = []
    sched.fire_times = []
    sched.time_generator = iter([])
    sched.stop_event = Event()
    sched.config_updated_event = Event()

    # Act & Assert: _should_send should swallow the exception and return False
    assert sched._should_send(fake_nd, datetime.now()) is False


def test__should_send_catches_DateAbsentError(monkeypatch):
    # Arrange: FakeNotifyDate that raises DateAbsentError
    fake_nd = FakeNotifyDate(
        title="T3",
        for_="none",
        should_return=False,
        raise_exc=scheduler.DateAbsentError(),
    )
    sched = scheduler.Scheduler.__new__(scheduler.Scheduler)
    sched.notify_dates = []
    sched.fire_times = []
    sched.time_generator = iter([])
    sched.stop_event = Event()
    sched.config_updated_event = Event()

    assert sched._should_send(fake_nd, datetime.now()) is False


# ─────────────────────────────────────────────────────────────────────────────
# 4) Tests for _notify_dates_and_fire_times (property)
# ─────────────────────────────────────────────────────────────────────────────


def test__notify_dates_and_fire_times_pairs_up_correctly():
    # Arrange: Two fake NotifyDates and two fire_times
    d1 = FakeNotifyDate("A", "x", should_return=False)
    d2 = FakeNotifyDate("B", "y", should_return=False)
    t1 = datetime(2025, 1, 1, 9, 0)
    t2 = datetime(2025, 1, 1, 10, 0)

    sched = scheduler.Scheduler.__new__(scheduler.Scheduler)
    sched.notify_dates = [d1, d2]
    sched.fire_times = [t1, t2]
    sched.time_generator = iter([])
    sched.stop_event = Event()
    sched.config_updated_event = Event()

    # Act:
    pairs = sched._notify_dates_and_fire_times

    # Assert: Should have exactly 4 pairs in the Cartesian product, in a consistent order
    assert len(pairs) == 4
    expected = [(d1, t1), (d1, t2), (d2, t1), (d2, t2)]
    assert pairs == expected


# ─────────────────────────────────────────────────────────────────────────────
# 5) Tests for send()
# ─────────────────────────────────────────────────────────────────────────────


def test_send_invokes_notify_only_when_should_send(monkeypatch, patch_notify):
    # Arrange:
    #   - One FakeNotifyDate that returns True for the earlier time,
    #   - One that returns False,
    #   - Fire times = [ t_early, t_late ]
    now = datetime.now()
    t_early = now + timedelta(minutes=1)
    t_late = now + timedelta(hours=1)

    # d_true should fire on t_early, but not on t_late
    d_true = FakeNotifyDate("HitEarly", "whoever", should_return=True)
    # d_false never fires
    d_false = FakeNotifyDate("NeverHit", "nowhere", should_return=False)

    sched = scheduler.Scheduler.__new__(scheduler.Scheduler)
    sched.notify_dates = [d_true, d_false]
    sched.fire_times = [t_early, t_late]
    sched.time_generator = iter([])
    sched.stop_event = Event()
    sched.config_updated_event = Event()

    # Act:
    sched.send()

    # Assert:
    #   - “HitEarly” should have been passed to notify exactly once (on the first matching t_early).
    #   - “NeverHit” should never appear.
    assert patch_notify == ["HitEarly"]


def test_send_handles_multiple_true_results(monkeypatch, patch_notify):
    # Arrange:
    now = datetime.now()
    t1 = now + timedelta(minutes=1)
    t2 = now + timedelta(minutes=2)

    # Two FakeNotifyDates, both returning True for both times
    d1 = FakeNotifyDate("D1", "x", should_return=True)
    d2 = FakeNotifyDate("D2", "y", should_return=True)

    sched = scheduler.Scheduler.__new__(scheduler.Scheduler)
    sched.notify_dates = [d1, d2]
    sched.fire_times = [t1, t2]
    sched.time_generator = iter([])
    sched.stop_event = Event()
    sched.config_updated_event = Event()

    # Act:
    sched.send()

    # Assert:
    #   Each (d1, t1), (d1, t2), (d2, t1), (d2, t2) is tested. As soon as a (nd → t) pair is True,
    #   we break for that nd and move to the next nd. So each nd should notify exactly once.
    assert sorted(patch_notify) == ["D1", "D2"]
    assert patch_notify.count("D1") == 1
    assert patch_notify.count("D2") == 1


# ─────────────────────────────────────────────────────────────────────────────
# 6) Tests for wait()
# ─────────────────────────────────────────────────────────────────────────────


def test_wait_returns_false_when_next_time_already_passed():
    # Arrange: A generator that yields “one time in the past,” so until_next_time == 0
    past_time = datetime.now() - timedelta(seconds=1)
    gen = iter([past_time])

    sched = scheduler.Scheduler.__new__(scheduler.Scheduler)
    sched.notify_dates = []
    sched.fire_times = [past_time]
    sched.time_generator = gen
    sched.stop_event = Event()
    sched.config_updated_event = Event()

    # Act:
    interrupted = sched.wait()

    # Assert:
    #   Because gen yields past_time, until_next_time = max((past_time - now).seconds, 0) == 0,
    #   so config_updated_event.wait(0) returns False (it’s not set), and stop_event.is_set() is False.
    assert interrupted is False


def test_wait_returns_true_when_config_updated_is_set_before_wait():
    # Arrange: A future time, but config_updated_event is already set.
    future_time = datetime.now() + timedelta(hours=1)
    gen = iter([future_time])

    sched = scheduler.Scheduler.__new__(scheduler.Scheduler)
    sched.notify_dates = []
    sched.fire_times = [future_time]
    sched.time_generator = gen
    sched.stop_event = Event()
    sched.config_updated_event = Event()
    sched.config_updated_event.set()  # simulate “config changed” before wait

    # Act:
    interrupted = sched.wait()

    # Assert: config_updated_event.wait(...) will return True immediately
    assert interrupted is True


def test_wait_returns_true_when_stop_event_is_set_during_wait():
    # Arrange:
    #   - A future time (so normally wait(...) would block),
    #   - A separate thread that sets stop_event after a tiny delay.
    future_time = datetime.now() + timedelta(minutes=5)
    gen = iter([future_time])

    sched = scheduler.Scheduler.__new__(scheduler.Scheduler)
    sched.notify_dates = []
    sched.fire_times = [future_time]
    sched.time_generator = gen
    sched.stop_event = Event()
    sched.config_updated_event = Event()

    # Kick off a thread that sets stop_event after 0.01s
    def set_stop_later():
        time_to_sleep = 0.01
        threading.Event().wait(timeout=time_to_sleep)
        sched.stop_event.set()
        sched.config_updated_event.set()

    killer = threading.Thread(target=set_stop_later, daemon=True)
    killer.start()

    # Act:
    interrupted = sched.wait()

    # Assert: since stop_event is set while waiting, wait() returns True
    assert interrupted is True
