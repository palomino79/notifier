import pytest
import threading
from datetime import datetime, timedelta
from threading import Event
from unittest import TestCase
from notify import scheduler
from notify.vars import TIMEZONE


class FakeScheduledDate:
    def __init__(
        self,
        description: str,
        notify_time: datetime,
        should_return: bool,
        date: str | None = None,
        raise_exc: Exception = None,
    ):
        """
        - title, for_ are just stored for logging/inspection
        - should_return controls what should_notify(...) returns
        - raise_exc, if not None, is raised when should_notify(...) is called
        """
        self.description = description
        self.notify_time = notify_time
        self.date = date
        self._should = should_return
        self._raise = raise_exc
        self._increment_called = False

    @classmethod
    def continue_with_errors(cls, **kwargs):
        if not kwargs.get("date"):
            return None
        return cls(**kwargs)

    def should_notify(self, t: datetime) -> bool:
        if self._raise:
            raise self._raise
        return self._should

    def increment_notify_time(self, *args, **kwargs):
        self._increment_called = True


@pytest.fixture(autouse=True)
def patch_send_notification(monkeypatch):
    called = []

    def fake_notify(nd_instance):
        called.append(nd_instance.description)

    monkeypatch.setattr("notify.scheduler.send_notification", fake_notify)
    return called


def get_preconfigured_scheduler(scheduled_dates=None, _generator=None):
    sched = scheduler.Scheduler.__new__(scheduler.Scheduler)
    sched._scheduled_dates = scheduled_dates or []
    sched.stop_event = Event()
    sched.schedule_updated_event = Event()
    if _generator:
        sched._generator = _generator
    return sched


def test_scheduled_dates_filters_invalid_data():
    """
    ScheduledDate MUST have a date, notify time, and description
    """
    good = {"date": "January 10", "notify_time": "12:00 PM", "description": "Good date"}
    bad = {"description": "Bad date"}

    sched = get_preconfigured_scheduler()
    sched.schedule = {"days": {"good": good, "bad": bad}}

    assert len(sched.scheduled_dates) == 1


def test_fire_times_sorts_in_correct_order():
    d1 = {"date": "January 10", "notify_time": "12:00 PM", "description": "Good date"}
    d2 = {"date": "January 11", "notify_time": "01:00 PM", "description": "Good date"}
    d3 = {"date": "January 12", "notify_time": "02:00 PM", "description": "Good date"}

    sched = get_preconfigured_scheduler()
    sched.schedule = {"days": {"d1": d1, "d2": d2, "d3": d3}}

    assert len(sched.fire_times) == 3
    last_time = None
    for i, d in enumerate(sched.fire_times):
        if last_time is None:
            last_time = d
        else:
            assert d > last_time
            last_time = d


def test_send_invokes_notify_once_per_iteration():
    d1 = {"date": "January 10", "notify_time": "12:00 PM", "description": "Good date"}
    d2 = {"date": "January 11", "notify_time": "01:00 PM", "description": "Good date"}
    d3 = {"date": "January 12", "notify_time": "02:00 PM", "description": "Good date"}

    sched = get_preconfigured_scheduler()
    sched.schedule = {"days": {"d1": d1, "d2": d2, "d3": d3}}


def test_fire_time_generator_raises_error():
    sched = get_preconfigured_scheduler()
    sched.schedule = {"days": {"d1": {}}}

    try:
        sched.next_fire_time
    except ValueError:
        assert True
    else:
        assert False


def test_fire_time_generator_inrements_notify_time(monkeypatch):
    """
    if t > now:
        yield t  (where t is fire time)
    then increment fire_times
    Q: How to make t always greater than now? Where t is a dateime replacing the hour
    and minute frm now with that of the notify_time.
    """
    d1 = {"date": "January 10", "notify_time": "12:00 PM", "description": "Good date"}

    sched = get_preconfigured_scheduler()
    sched.schedule = {"days": {"d1": d1}}

    notify_1 = sched.scheduled_dates[0].notify_time

    class fake_datetime:
        @staticmethod
        def now(*args, **kwargs):
            return datetime.now(tz=TIMEZONE) - timedelta(days=10000)

    monkeypatch.setattr("notify.scheduler.datetime", fake_datetime)

    sched.next_fire_time
    sched.next_fire_time
    notify_2 = sched.scheduled_dates[0].notify_time
    delta = notify_2 - notify_1
    assert delta.days == 1


def test_send_invokes_notify_only_when_should_send(patch_send_notification):
    now = datetime.now()
    t_early = now + timedelta(minutes=1)
    t_late = now + timedelta(hours=1)
    d_true = FakeScheduledDate("HitEarly", t_early, should_return=True)
    d_false = FakeScheduledDate("NeverHit", t_late, should_return=False)

    sched = get_preconfigured_scheduler([d_true, d_false])
    sched.send()

    assert patch_send_notification == ["HitEarly"]


def test_send_handles_multiple_true_results(monkeypatch, patch_send_notification):
    now = datetime.now()
    t1 = now + timedelta(minutes=1)
    t2 = now + timedelta(minutes=2)

    d1 = FakeScheduledDate("D1", t1, should_return=True)
    d2 = FakeScheduledDate("D2", t2, should_return=True)

    sched = get_preconfigured_scheduler([d1, d2])
    sched.send()

    assert sorted(patch_send_notification) == ["D1", "D2"]
    assert patch_send_notification.count("D1") == 1
    assert patch_send_notification.count("D2") == 1


def test_wait_returns_false_when_next_time_already_passed():
    """
    This does not need to be tested because the nature of the
    underlying generator makes this functionally impossible.
    """
    past_time = datetime.now() - timedelta(seconds=1)

    sched = get_preconfigured_scheduler(
        [FakeScheduledDate("A", datetime.now(), should_return=True)],
        _generator=iter([past_time]),
    )

    interrupted = sched.wait()
    assert interrupted is False


def test_wait_returns_true_when_schedule_updated_is_set_before_wait():
    future_time = datetime.now() + timedelta(hours=1)

    sched = get_preconfigured_scheduler(_generator=iter([future_time]))
    sched.schedule_updated_event.set()
    interrupted = sched.wait()

    assert interrupted is True


def test_wait_returns_true_when_schedule_updatd_event_is_set_during_wait():
    """
    This test is fine because that can happen, if unlikely to occur.
    """
    future_time = datetime.now() + timedelta(minutes=5)

    sched = get_preconfigured_scheduler(_generator=iter([future_time]))

    def set_stop_later():
        time_to_sleep = 0.02
        threading.Event().wait(timeout=time_to_sleep)
        sched.schedule_updated_event.set()

    killer = threading.Thread(target=set_stop_later, daemon=True)
    killer.start()

    interrupted = sched.wait()

    assert interrupted is True


def test_wait_returns_true_when_stop_event_is_set_during_wait():
    """
    This test is fine because that can happen, if unlikely to occur.
    """
    future_time = datetime.now() + timedelta(minutes=5)
    sched = get_preconfigured_scheduler(_generator=iter([future_time]))

    def set_stop_later():
        time_to_sleep = 0.02
        threading.Event().wait(timeout=time_to_sleep)
        sched.stop_event.set()
        sched.schedule_updated_event.set()

    killer = threading.Thread(target=set_stop_later, daemon=True)
    killer.start()
    interrupted = sched.wait()
    assert interrupted is True
