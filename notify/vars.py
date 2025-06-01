import os
from pytz import timezone  # type: ignore

TIMEZONE = timezone(os.environ.get("TZ", "US/Eastern"))
SCHEDULE_PATH = os.environ.get("SCHEDULE_PATH")
PUSH_SERVICE_URL = os.environ.get("SERVICE")
TOPIC = os.environ.get("TOPIC")
NOTIFICATION_URL = os.path.join(PUSH_SERVICE_URL or "", TOPIC or "")
