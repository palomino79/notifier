from datetime import datetime, timedelta
from pytz import timezone  # type: ignore
from typing import List
import os

TIMEZONE = timezone(os.environ.get("TZ", "US/Eastern"))


"""
I feel like one of these should be an exhaustible
generator.
"""


def get_next_time(next_times: List[datetime]):
    now = datetime.now(tz=TIMEZONE)
    while True:
        for time in next_times:
            if time > now:
                yield time
        next_times = [t + timedelta(days=1) for t in next_times]


def collect_notification_times(res: dict):
    times = []
    for _, value in res.items():
        for _, item in value.items():
            time = item.get("notify_time")
            if not time:
                raise ValueError("No time specified.")

            now = datetime.now(tz=TIMEZONE)
            dt = datetime.strptime(
                f"{time} {now.day} {now.month} {now.year}", "%I:%M %d %m %y"
            )
            dt = dt.astimezone(TIMEZONE)
            times.append(dt)
    times = list(set(times))
    return sorted(times)
