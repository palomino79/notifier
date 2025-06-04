from datetime import datetime
import yaml  # type: ignore
import unittest
from datetime import timedelta
from notify import scheduled_dates
from notify.scheduled_dates import NotifyTimeAbsentError
from functools import cached_property


def test_collect_weekday():
    collected = scheduled_dates.collect_weekday("Monday", 5, 2025)
    expected = [
        datetime(year=2025, month=5, day=5),
        datetime(year=2025, month=5, day=12),
        datetime(year=2025, month=5, day=19),
        datetime(year=2025, month=5, day=26),
    ]
    assert collected == expected


class TestScheduledDate(unittest.TestCase):
    def setUp(self):
        base_yml = """
birthdays:
    josh:
        description: Josh's birthday
        date: December 5
        notify_before_days: 2
        notify_time: 12:00 PM
holidays:
    mothers_day:
        description: mother's day
        date:
            month: May
            weekday: Sunday
            day_n: 2
        notify_before_days: 3
        notify_time: 12:00 PM
    july_fourth:
        description: Fourth of July
        date: July 4
    new_years:
        description: New Years
        date: January 1
        notify_time: 12:00 PM
        notify_before_days: 2
        push_url: http://foo.bar.baz
        push_topic: my-topic
        """

        self.base_data = yaml.load(base_yml, yaml.Loader)

    @cached_property
    def josh_birthday(self):
        d = self.base_data.get("birthdays").get("josh")
        return scheduled_dates.ScheduledDate(**d)

    @cached_property
    def mothers_day(self):
        d = self.base_data.get("holidays").get("mothers_day")
        this = scheduled_dates.ScheduledDate(**d)
        print(this)
        return this

    @cached_property
    def july_fourth(self):
        d = self.base_data.get("holidays").get("july_fourth")
        return scheduled_dates.ScheduledDate(**d)

    @cached_property
    def new_years(self):
        d = self.base_data.get("holidays").get("new_years")
        return scheduled_dates.ScheduledDate(**d)

    def test_missing_notify_time(self):
        with self.assertRaises(TypeError):
            _ = self.july_fourth

    def test_datetime(self):
        print(self.mothers_day.date)
        cd = self.mothers_day.datetime
        print(cd)
        dt = datetime(2025, 5, 11, 12, 0, 0, tzinfo=scheduled_dates.TIMEZONE)
        print(dt)
        self.assertEqual(cd, dt)

    def test_should_notify(self):
        trigger_times = [
            datetime(2025, 5, 8, 12, 0, tzinfo=scheduled_dates.TIMEZONE),
            datetime(2025, 5, 9, 12, 0, tzinfo=scheduled_dates.TIMEZONE),
            datetime(2025, 5, 10, 12, 0, tzinfo=scheduled_dates.TIMEZONE),
            datetime(2025, 5, 11, 12, 0, 1, tzinfo=scheduled_dates.TIMEZONE),
            datetime(2025, 5, 11, 11, 59, 59, tzinfo=scheduled_dates.TIMEZONE),
            datetime(2025, 5, 12, 12, 0, tzinfo=scheduled_dates.TIMEZONE),
            datetime(2025, 5, 13, 0, 0, tzinfo=scheduled_dates.TIMEZONE),
            datetime(2025, 5, 12, 12, 0),
        ]
        should_notifies = [self.mothers_day.should_notify(x) for x in trigger_times]
        values = [True, True, True, False, False, False, False, False]
        self.assertEqual(should_notifies, values)

        trigger_times = [
            datetime(2025, 12, 28, 12, 0, tzinfo=scheduled_dates.TIMEZONE),
            datetime(2025, 12, 31, 12, 0, tzinfo=scheduled_dates.TIMEZONE),
            datetime(2025, 12, 31, 13, 0, tzinfo=scheduled_dates.TIMEZONE),
            datetime(2026, 1, 2, 0, 0, tzinfo=scheduled_dates.TIMEZONE),
        ]

        should_notifies = [self.new_years.should_notify(x) for x in trigger_times]
        values = [False, True, False, False]
        self.assertEqual(should_notifies, values)

    def test_push_path_set(self):
        self.assertEqual(self.new_years.full_push_path, "http://foo.bar.baz/my-topic")

    def test_push_path_unset(self):
        self.assertIsNone(self.mothers_day.full_push_path)

    def test_increment_notify_time(self):
        current_notify = self.mothers_day.notify_time
        self.mothers_day.increment_notify_time(1)
        next_notify = self.mothers_day.notify_time
        self.assertTrue(next_notify - current_notify == timedelta(days=1))
