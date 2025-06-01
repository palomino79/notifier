import os
from pathlib import Path
from pytz import timezone  # type: ignore

TIMEZONE = timezone(os.environ.get("TZ", "US/Eastern"))
CONFIG_PATH = os.environ.get("CONFIG_PATH", "notify.yml")
SERVICE = os.environ.get("SERVICE", "ntfy")
TOPIC = os.environ.get("TOPIC", "birthday-alerts")
