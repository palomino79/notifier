import os
from pytz import timezone  # type: ignore

TIMEZONE = timezone(os.environ.get("TZ", "US/Eastern"))
CONFIG_BASEPATH = os.environ.get("CONFIG_BASEPATH", os.path.abspath(__file__))
SERVICE = os.environ.get("SERVICE", "ntfy")
TOPIC = os.environ.get("TOPIC", "birthday-alerts")
