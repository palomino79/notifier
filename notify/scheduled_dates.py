from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Union, List, Optional
import os
from .vars import TIMEZONE
from .log_setup import logger


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


@dataclass(kw_only=True, order=True)
class ScheduledDate:
    date: dict | str | datetime
    notify_time: str | datetime
    datetime: Optional[datetime] = field(default=None)
    description: str
    notify_before_days: int = field(default=0)
    push_url: Optional[str] = field(default=None)
    push_topic: Optional[str] = field(default=None)

    @classmethod
    def continue_with_errors(cls, *args, **kwargs):
        try:
            return cls(**kwargs)
        except Exception as e:
            logger.error(e, exc_info=True)
        return None

    def __post_init__(self):
        """
        Handle upgrade of primitive datatypes (dicts, strs)
        to datetimes
        """
        if isinstance(self.date, str):
            this = f"{self.date} {self.now.year}"  # type: ignore
            self.date = datetime.strptime(this, "%B %d %Y")
        elif isinstance(self.date, dict):
            month = self.date["month"]  # type: ignore
            weekday = self.date["weekday"]  # type: ignore
            day_n = self.date["day_n"]  # type: ignore

            weekdays = collect_weekday(weekday, month, self.now.year)  # type: ignore
            if not isinstance(day_n, int):
                if isinstance(day_n, str) and day_n != "last":
                    raise ValueError(f"Expected 'last', got '{day_n}'")
                self.date = weekdays[-1]
            self.date = weekdays[day_n - 1]
        elif isinstance(self.date, datetime):
            pass
        else:
            raise TypeError("Expected dict or str, got " + str(type(self.date)))

        if not self.notify_time:
            raise NotifyTimeAbsentError
        if isinstance(self.notify_time, str):
            t = datetime.strptime(self.notify_time, "%I:%M %p").time()
            self.notify_time = self.now.replace(  # type: ignore
                hour=t.hour,
                minute=t.minute,
                second=0,
                microsecond=0,
                tzinfo=TIMEZONE,
            )
        self.datetime = self.notify_time.replace(
            day=self.date.day,  # type: ignore
            month=self.date.month,  # type: ignore
        )

    def increment_notify_time(self, days: int):
        if isinstance(self.notify_time, datetime):
            self.notify_time = self.notify_time + timedelta(days=days)

    @property
    def full_push_path(self):
        if self.push_url and self.push_topic:
            return os.path.join(self.push_url, self.push_topic)

    @property
    def now(self) -> datetime:  # type: ignore
        return datetime.now(tz=TIMEZONE)

    def should_notify(self, trigger_time: datetime) -> bool:  # type: ignore
        if self.datetime:
            try:
                delta: timedelta = self.datetime - trigger_time
            except TypeError:
                return False
            else:
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
