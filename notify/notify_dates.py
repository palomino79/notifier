from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Union, List
from functools import cached_property
import logging
from .vars import TIMEZONE

logger = logging.getLogger("notify")
logging.basicConfig()


class NotifyTimeAbsentError(Exception): ...


class DateAbsentError(Exception): ...


weekday_map = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "sunday",
)

month_map = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)


def collect_weekday(
    day_of_week: Union[str, int], month: Union[str, int], year: int
) -> List[datetime]:
    if isinstance(day_of_week, str):
        day_of_week = weekday_map.index(day_of_week.lower())
    if isinstance(month, str):
        month = month_map.index(month.lower()) + 1

    res = []
    current_date = datetime(year=year, month=month, day=1)
    while True:
        if current_date.month != month:
            break
        if current_date.weekday() == day_of_week:
            res.append(current_date)
        current_date += timedelta(days=1)
    return res


@dataclass
class NotifyDate:
    data: dict

    @cached_property
    def for_(self):
        return self.data.get("for")

    @cached_property
    def title(self):
        return self.data.get("title", "No title.")

    @cached_property
    def date(self) -> datetime | dict:
        date = self.data.get("date")
        if not date:
            raise DateAbsentError
        if isinstance(date, str):
            this = f"{date} {self.now.year}"
            return datetime.strptime(this, "%B %d %Y")
        elif isinstance(date, dict):
            return date
        else:
            raise TypeError("Unexpected date format found: " + str(type(date)))

    @property
    def now(self):
        return datetime.now(tz=TIMEZONE)

    @cached_property
    def notify_before_days(self) -> int:
        return self.data.get("notify_before_days", 0)

    @property
    def notify_time(self):
        notify_time = self.data.get("notify_time")
        if not notify_time:
            raise NotifyTimeAbsentError
        # time without date or tzinfo
        t = datetime.strptime(f"{notify_time}", "%I:%M %p").time()
        return datetime(
            year=self.now.year,
            month=self.now.month,
            day=self.now.day,
            hour=t.hour,
            minute=t.minute,
            tzinfo=TIMEZONE,
        )

    def should_notify(self, trigger_time: datetime) -> bool:
        if self.datetime:
            try:
                delta: timedelta = self.datetime - trigger_time
            except TypeError:
                return False
            if delta.days < 0:
                """
                This deals with the scenario where you have, for example
                an alert for January 1st, YEAR+1 and you want it to fire
                on, say, December 31st, YEAR.
                """
                dt = self.datetime.replace(year=self.datetime.year + 1)
                delta = dt - trigger_time
            if (delta.days > 0) and (delta.days <= self.notify_before_days):
                seconds = delta.total_seconds()
                return not (seconds % (60 * 60 * 24))
        return False

    @cached_property
    def datetime(self) -> datetime:
        if isinstance(self.date, datetime):
            return self.notify_time.replace(
                year=self.now.year, month=self.date.month, day=self.date.day
            )
        elif isinstance(self.date, dict):
            return self.notify_time.replace(
                year=self.conditional_date.year,  # type: ignore
                month=self.conditional_date.month,  # type: ignore
                day=self.conditional_date.day,  # type: ignore
            )
        raise TypeError(f"Expected string or dict for self.date. Got {type(self.date)}")

    @cached_property
    def conditional_date(self) -> datetime:  # type: ignore
        if not isinstance(self.date, dict):
            raise TypeError("Cannot call conditional date without date dictionary.")
        month = self.date["month"]  # type: ignore
        weekday = self.date["weekday"]  # type: ignore
        day_n = self.date["day_n"]  # type: ignore

        weekdays = collect_weekday(weekday, month, self.now.year)
        if not isinstance(day_n, int):
            if isinstance(day_n, str) and day_n != "last":
                raise ValueError(f"Expected `last`, got {day_n}")
            return weekdays[-1]
        return weekdays[day_n - 1]
