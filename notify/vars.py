import os
from pytz import timezone  # type: ignore

TIMEZONE = timezone(os.environ.get("TZ", "US/Eastern"))
SCHEDULE_PATH = os.environ.get("SCHEDULE_PATH")
SERVICE = os.environ.get("SERVICE")
TOPIC = os.environ.get("TOPIC")
