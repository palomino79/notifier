import pytest  # type: ignore
import threading
import time
from datetime import datetime, timedelta
from queue import Queue, Empty
from threading import Event
import notify


@pytest.fixture(autouse=True)
def patch_notification(monkeypatch):
    """
    Intercept calls to notify() so we can see which titles get “fired.”
    """
    called = []

    def fake_notify(nd_instance):
        called.append(nd_instance.title)

    monkeypatch.setattr("notify.notify", fake_notify)
    print(called)
    return called


@pytest.fixture
def sample_config():
    """
    Return a simple dict that produces exactly one NotifyDate
    whose .should_notify() will be True when we pass the matching time.
    For example: a date = “tomorrow at noon” with notify_before_days=0.
    """
    tomorrow = datetime.now() + timedelta(days=1)
    date_str = tomorrow.strftime("%B %d")  # e.g. "May 21" if today is May 20
    # Build a dict in the shape your code expects: top‐level keys → sub‐dict.
    return {
        "foo": {
            "bar": {
                "title": "Test Event",
                "for_": "me",
                "date": date_str,
                "notify_time": tomorrow.strftime("%I:%M %p"),  # "12:00 PM"
                "notify_before_days": 0,
            }
        }
    }


def test_run_cron_fires_immediately_when_time_matches(
    monkeypatch, sample_config, patch_notification
):
    q: Queue = Queue()
    config_updated = Event()
    stop_event = Event()

    # 1) Monkey-patch the scheduler functions so that `get_next_time(...)` yields “now”
    def fake_collect_times(data):
        # Return a list of datetime objects exactly “tomorrow at 12:00 PM”
        return [datetime.now()]

    monkeypatch.setattr("notify.collect_notification_times", fake_collect_times)

    def fake_get_next_time(trigger_list):
        # Return a generator that yields the only element immediately, then stops
        yield trigger_list[0]
        while True:
            # After first yield, sleep briefly, then stop the thread in our test
            time.sleep(0.1)
            return
        # Alternatively, if you want a clean StopIteration after the first:
        # yield trigger_list[0]
        # return

    monkeypatch.setattr("notify.get_next_time", fake_get_next_time)

    # 2) Monkey-patch `build_notify_dates_list` so it returns
    #    a list of NotifyDate objects that we know will “should_notify” immediately.
    #    We already have sample_config. Our NotifyDate constructor will parse it.
    #    We also want to monkey-patch `NotifyDate.should_notify(...)` to return True:
    class DummyNotifyDate:
        def __init__(self, data):
            self.title = data.get("title", "dummy")
            self.for_ = data.get("for_", "")
            self.data = data

        def should_notify(self, t):
            # Always return True on the very first call
            return True

    monkeypatch.setattr("notify.NotifyDate", DummyNotifyDate)
    # Now `build_notify_dates_list` will do: `[DummyNotifyDate(x) for …]`
    # We can let it run unmodified.

    # 3) Start run_cron in a thread
    t = threading.Thread(
        target=notify.run_cron,
        args=(q, config_updated, stop_event, sample_config),
        daemon=True,
    )
    t.start()

    # 4) Wait a short moment for the thread to wake up, process "next_time == now", fire, and call notify()
    time.sleep(0.2)

    # Since `should_notify` always returned True, `notify()` (patched to `fake_notify`) should have been called once
    assert "Test Event" in patch_notification

    # 5) Now signal the thread to stop and join
    stop_event.set()
    t.join(timeout=1)
    assert not t.is_alive()


def test_run_cron_reloads_config_on_queue_update(
    monkeypatch, sample_config, patch_notification
):
    """
    This test ensures that if a fresh config arrives via `q.put(...)`,
    run_cron picks it up and rebuilds notify_dates + trigger_times.
    """
    q: Queue = Queue()
    config_updated = Event()
    stop_event = Event()

    # 1) Start with sample_config. Monkey-patch so that get_next_time yields a time far in the future.
    far_future = datetime.now() + timedelta(days=365)
    monkeypatch.setattr(
        "notify.collect_notification_times",
        lambda data: [far_future],
    )
    monkeypatch.setattr(
        "notify.get_next_time",
        lambda x: (t for t in x),  # simple generator that yields once
    )

    # We still allow build_notify_dates_list to be real. But force should_notify to be False initially
    # so that no notify() is called until we push a new config.
    class DummyNotifyDateNoFire:
        def __init__(self, data):
            self.title = data.get("title", "")
            self.for_ = data.get("for_", "")
            self.data = data

        def should_notify(self, t):
            return False

    monkeypatch.setattr("notify.NotifyDate", DummyNotifyDateNoFire)

    # 2) Start run_cron in a thread
    t = threading.Thread(
        target=notify.run_cron,
        args=(q, config_updated, stop_event, sample_config),
        daemon=True,
    )
    t.start()

    # 3) Give it a moment so it computes far_future, waits on `config_updated` for that interval
    time.sleep(0.1)
    assert not patch_notification, "No notifications should have fired yet"

    # 4) Build a new config dict that has a trigger “right now”
    now_config = {
        "foo": {
            "bar": {
                "title": "Immediate Event",
                "for_": "you",
                "date": datetime.now().strftime("%B %d"),
                "notify_time": datetime.now().strftime("%I:%M %p"),
                "notify_before_days": 0,
            }
        }
    }

    # Push that new config into the queue
    q.put(now_config)
    # Signal that config has been updated, so run_cron will break out of its wait
    config_updated.set()

    # 5) Wait a short moment for run_cron to pick up the new config, rebuild, and fire notify
    time.sleep(0.2)
    assert "Immediate Event" in patch_notification

    # 6) Shutdown
    stop_event.set()
    t.join(timeout=1)
    assert not t.is_alive()
