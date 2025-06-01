import os
from typing import Any, Callable
from pytz import timezone  # type: ignore


def get_var(name: str, default: Any = None, wrap: Callable | None = None):
    res = os.environ.get(name, default)
    if isinstance(res, str) and isinstance(default, bool):
        if res.lower() in ("false", "0"):
            return False
        elif res.lower() in ("true", "1"):
            return True
    if wrap:
        return wrap(res)
    return res


TEST_ON_START = get_var("TEST_ON_START", False)
SUPPRESS_SSL_WARNINGS = get_var("SUPPRESS_SSL_WARNINGS", True)
TIMEZONE = get_var("TZ", "US/Eastern", timezone)
SCHEDULE_PATH = get_var("SCHEDULE_PATH")
PUSH_SERVICE_URL = get_var("PUSH_SERVICE_URL")
TOPIC = get_var("TOPIC")
NOTIFICATION_URL = os.path.join(PUSH_SERVICE_URL or "", TOPIC or "")
