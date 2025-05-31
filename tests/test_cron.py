# tests/test_notifications.py
from datetime import datetime, timedelta
from unittest.mock import patch
import cron


def test_get_next_times():
    fixed_now = datetime(2025, 5, 27, 8, 0, tzinfo=cron.TIMEZONE)

    class DummyDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    with patch.object(cron, "datetime", DummyDateTime):
        notify_times = [datetime(2025, 5, 27, 9, 0, tzinfo=cron.TIMEZONE)]
        gen = cron.get_next_time(notify_times)
        collected_times = [next(gen) for _ in range(2)]
    assert collected_times[0] == notify_times[0]
    assert collected_times[1] == notify_times[0] + timedelta(days=1)


def test_collect_notification_times_basic():
    # 2 entries have notify_time, 1 does not
    sample = {
        "birthdays": {
            "josh": {
                "title": "Josh's birthday",
                "for": "Josh Smith",
                "date": "September 22",
                "notify_before_days": 2,
                "notify_time": "12:00 PM",
                "repeat": True,
            }
        },
        "holidays": {
            "july_fourth": {
                "title": "Fourth of July",
                "date": "July 4th",
                "notify_time": "01:00 PM",
            },
        },
    }
    fixed_now = datetime(2025, 5, 27, 8, 0, tzinfo=cron.TIMEZONE)

    class DummyDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    with patch.object(cron, "datetime", DummyDateTime):
        times = cron.collect_notification_times(sample)
        print(times)

    expected_dt_a = datetime(2025, 5, 27, 12, 0, tzinfo=cron.TIMEZONE)
    expected_dt_b = datetime(2025, 5, 27, 13, 0, tzinfo=cron.TIMEZONE)
    assert times == [expected_dt_a, expected_dt_b]
