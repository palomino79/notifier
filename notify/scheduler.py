from dataclasses import dataclass
from datetime import datetime
from typing import List, Generator
from threading import Event
import logging
import requests
from .notify_dates import NotifyDate, NotifyTimeAbsentError, DateAbsentError
from .vars import SERVICE, TOPIC

logger = logging.getLogger(__file__)
logging.basicConfig()


def notify(nd: NotifyDate):
    title = nd.title
    for_ = nd.for_
    date: datetime = nd.date if not isinstance(nd.date, dict) else nd.conditional_date
    ctime = date.ctime()
    message = f"Upcoming reminder: {title}. For: {for_}. When: {ctime}"
    try:
        requests.post(f"http://{SERVICE}/{TOPIC}", data=message)
    except requests.HTTPError as e:
        print(e)


@dataclass
class Scheduler:
    notify_dates: List[NotifyDate]
    fire_times: List[datetime]
    time_generator: Generator
    stop_event: Event
    config_updated_event: Event

    @property
    def _notify_dates_and_fire_times(self):
        return [(nd, t) for nd in self.notify_dates for t in self.fire_times]

    def _should_send(self, nd: NotifyDate, t: datetime) -> bool:
        try:
            if nd.should_notify(t):
                return True
        except NotifyTimeAbsentError:
            logger.error(f"No notify_time set for notify_date {nd.title}")
        except DateAbsentError:
            logger.error(f"No date set for notify_date {nd.title}")
        except (ValueError, TypeError) as e:
            logger.error(e, exc_info=True)
        return False

    def send(self):
        for nd in self.notify_dates:
            for t in self.fire_times:
                if self._should_send(nd, t):
                    notify(nd)
                    break

    def wait(self) -> bool:
        """
        Returns True if the wait was interrupted.
        Otherwise False (wait completed)
        """
        next_time = next(self.time_generator)  # type: ignore
        until_next_time = max((next_time - datetime.now()).total_seconds(), 0)
        wait_interrupted = (
            self.config_updated_event.wait(until_next_time) or self.stop_event.is_set()
        )
        return wait_interrupted
