from datetime import datetime, timedelta
from pytz import timezone  # type: ignore
from typing import List
import os

TIMEZONE = timezone(os.environ.get("TZ", "US/Eastern"))


def get_next_time(next_times: List[datetime]):
    now = datetime.now(tz=TIMEZONE)
    while True:
        for time in next_times:
            if time > now:
                yield time
        next_times = [t + timedelta(days=1) for t in next_times]


def collect_notification_times(res: dict, now: None | datetime = None):
    now = now or datetime.now(tz=TIMEZONE)
    times = []
    for _, value in res.items():
        for _, item in value.items():
            time = item.get("notify_time")
            if not time:
                print("No time found. Continuing.")
                continue
            temp = datetime.strptime(time, "%I:%M %p").time()
            dt = now.replace(
                hour=temp.hour, minute=temp.minute, second=0, microsecond=0
            )
            times.append(dt)
    times = list(set(times))
    return sorted(times)
