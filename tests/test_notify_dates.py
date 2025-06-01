from datetime import datetime
import yaml  # type: ignore
import unittest
from notify import notify_dates
from notify.notify_dates import NotifyTimeAbsentError
from functools import cached_property


def test_collect_weekday():
    collected = notify_dates.collect_weekday("Monday", 5, 2025)
    expected = [
        datetime(year=2025, month=5, day=5),
        datetime(year=2025, month=5, day=12),
        datetime(year=2025, month=5, day=19),
        datetime(year=2025, month=5, day=26),
    ]
    assert collected == expected


class TestNotifyDate(unittest.TestCase):
    def setUp(self):
        base_yml = """
birthdays:
    josh:
        title: Josh's birthday
        for: Josh Smith
        date: December 5
        notify_before_days: 2
        notify_time: 12:00 PM
        repeat: true
holidays:
    mothers_day:
        title: mother's day
        date:
            month: May
            weekday: Sunday
            day_n: 2
        notify_before_days: 3
        repeat: true
        notify_time: 12:00 PM
    july_fourth:
        title: Fourth of July
        date: July 4
        """

        self.base_data = yaml.load(base_yml, yaml.Loader)

    @cached_property
    def josh_birthday(self):
        d = self.base_data.get("birthdays").get("josh")
        return notify_dates.NotifyDate(d)

    @cached_property
    def mothers_day(self):
        d = self.base_data.get("holidays").get("mothers_day")
        return notify_dates.NotifyDate(d)

    @cached_property
    def july_fourth(self):
        d = self.base_data.get("holidays").get("july_fourth")
        return notify_dates.NotifyDate(d)

    def test_missing_notify_time_raises_error(self):
        with self.assertRaises(NotifyTimeAbsentError):
            _ = self.july_fourth.notify_time

    def test_conditional_date(self):
        # implicitly tests collect_weekday
        cd = self.mothers_day.conditional_date
        xd = datetime(2025, 5, 11)
        self.assertEqual(cd, xd)

    def test_datetime(self):
        cd = self.mothers_day.datetime
        dt = datetime(2025, 5, 11, 12, 0, 0, tzinfo=notify_dates.TIMEZONE)
        self.assertEqual(cd, dt)

    def test_should_notify(self):
        trigger_times = [
            datetime(2025, 5, 8, 12, 0, tzinfo=notify_dates.TIMEZONE),
            datetime(2025, 5, 9, 12, 0, tzinfo=notify_dates.TIMEZONE),
            datetime(2025, 5, 10, 12, 0, tzinfo=notify_dates.TIMEZONE),
            datetime(2025, 5, 11, 12, 0, 1, tzinfo=notify_dates.TIMEZONE),
            datetime(2025, 5, 11, 11, 59, 59, tzinfo=notify_dates.TIMEZONE),
            datetime(2025, 5, 12, 12, 0, tzinfo=notify_dates.TIMEZONE),
            datetime(2025, 5, 13, 0, 0, tzinfo=notify_dates.TIMEZONE),
            datetime(2025, 5, 12, 12, 0),
        ]
        should_notifies = [self.mothers_day.should_notify(x) for x in trigger_times]
        values = [True, True, True, False, False, False, False, False]
        self.assertEqual(should_notifies, values)
