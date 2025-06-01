import os
from pytz import timezone  # type: ignore

TIMEZONE = timezone(os.environ.get("TZ", "US/Eastern"))
CONFIG_PATH = os.environ.get("CONFIG_PATH")
SERVICE = os.environ.get("SERVICE")
TOPIC = os.environ.get("TOPIC")
