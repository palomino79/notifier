from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Union, List, Optional
from functools import cached_property
import logging

logger = logging.getLogger("notify")
logging.basicConfig()


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
        month = month_map.index(month.lower())

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
    def date(self):
        return self.data.get("date")

    @cached_property
    def now(self):
        return

    @cached_property
    def notify_before_days(self):
        return self.data.get("notify_before_days")

    def trigger_time(self, notify_time: str) -> datetime:
        day = self.now.day
        month = self.now.month
        year = self.now.year
        return datetime.strptime(
            f"{notify_time} {day} {month} {year}", "%I:%M %d %m %y"
        )

    def should_notify(self, trigger_time: datetime) -> bool:
        if self.datetime:
            delta: timedelta = self.datetime - trigger_time
            if delta.days <= self.notify_before_days:
                seconds = delta.seconds
                return not delta.seconds or not (seconds % (60 * 60 * 24))
        return False

    @cached_property
    def datetime(self) -> Optional[datetime]:
        try:
            if isinstance(self.date, str):
                time = self.data.get("notify_time")
                date = self.data.get("date")
                as_dt = datetime.strptime(
                    f"{time} {date} {self.now.year}", "%I:%M %B %d %Y"
                )
            elif isinstance(self.date, dict):
                as_dt = self.conditional_date
        except (ValueError, KeyError) as e:
            logging.error(e, exc_info=True)
            return None
        else:
            return as_dt

    @cached_property
    def conditional_date(self) -> datetime:
        month = self.data.date["month"]  # type: ignore
        weekday = self.data.date["weekday"]  # type: ignore
        day_n = self.data.date["day_n"]  # type: ignore

        weekdays = collect_weekday(weekday, month, self.now.year)
        if not isinstance(day_n, int):
            if not isinstance(day_n, str) and day_n != "last":
                raise ValueError(f"Expected `last`, got {day_n}")
            return weekdays[-1]
        return weekdays[day_n - 1]
