from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Generator, Optional
from threading import Event
from time import sleep
from .scheduled_dates import ScheduledDate
from .vars import TIMEZONE
from .log_setup import logger
from .send_notification import send_notification


@dataclass
class Scheduler:
    schedule: dict
    stop_event: Event
    schedule_updated_event: Event
    _scheduled_dates: List[ScheduledDate] = field(default_factory=list)
    _generator: Optional[Generator] = field(default=None)

    @property
    def scheduled_dates(self) -> List[ScheduledDate]:
        if not self._scheduled_dates:
            this = [
                ScheduledDate.continue_with_errors(**j)
                for i in self.schedule.values()
                for j in i.values()
            ]
            self._scheduled_dates = [x for x in this if x]
            if not self._scheduled_dates:
                raise ValueError("No dates provided.")
        return self._scheduled_dates

    @property
    def next_fire_time(self):
        if not self._generator:
            self._generator = self.fire_time_generator()
        return next(self._generator)

    def fire_time_generator(self) -> Generator:
        while True:
            if not self.fire_times:
                raise StopIteration
            for t in self.fire_times:
                now = datetime.now(tz=TIMEZONE)
                if t > now:
                    yield t
            for s in self.scheduled_dates:
                s.increment_notify_time(1)

    @property
    def fire_times(self):
        return sorted(list({n.notify_time for n in self.scheduled_dates}))

    def send(self):
        for sd in self.scheduled_dates:
            for t in self.fire_times:
                if sd.should_notify(t):
                    send_notification(sd)
                    break

    def wait(self) -> bool:
        """
        Returns True if the wait was interrupted.
        Otherwise False (wait completed)
        """
        try:
            nft = self.next_fire_time
            until_next_time = max((nft - datetime.now()).total_seconds(), 0)
            logger.info(
                f"New sleep target: {nft.ctime()}. Sleeping for {until_next_time} seconds."
            )
            wait_interrupted = (
                self.schedule_updated_event.wait(until_next_time)
                or self.stop_event.is_set()
            )
        except StopIteration:
            sleep(5)
            return False
        return wait_interrupted
