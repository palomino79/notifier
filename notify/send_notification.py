from .vars import NOTIFICATION_URL, SUPPRESS_SSL_WARNINGS
from .scheduled_dates import ScheduledDate
from .log_setup import logger
import requests


if SUPPRESS_SSL_WARNINGS:
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def post_message(message: str, url: str):
    try:
        requests.post(url, data=message, verify=False)
    except requests.HTTPError as e:
        print(e)


def send_notification(sd: ScheduledDate):
    description = sd.description
    ctime = sd.datetime.ctime()  # type: ignore
    message = f"Upcoming reminder: {description}. When: {ctime}"
    push_path = sd.full_push_path or NOTIFICATION_URL
    logger.info(f'Posting message: "{message}" to {push_path}')
    post_message(message, url=push_path)
