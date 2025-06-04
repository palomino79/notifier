import hashlib
from datetime import datetime
from typing import Callable
from queue import Queue, Empty
from threading import Thread, Event
from functools import cached_property
from yaml import load, Loader  # type: ignore
from .scheduler import Scheduler
from .scheduled_dates import ScheduledDate
from .log_setup import logger


def compute_file_hash(file_path: str):
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def load_schedule(file_path: str):
    with open(file_path, "r") as infile:
        res = load(infile, Loader)
        return res


class ScheduleMonitor(Thread):
    def __init__(
        self,
        file_path: str,
        on_change: Callable,
        poll_interval: float = 2.0,
        daemon=True,
    ):
        self._file_path = file_path
        self._on_change = on_change
        self._poll_interval = poll_interval
        self._stop_event = Event()
        self._last_hash = compute_file_hash(file_path)
        super().__init__(daemon=daemon)

        logger.info(
            f"ScheduleMonitor started with polling interval of {poll_interval} seconds."
        )

    @cached_property
    def last_hash(self):
        """
        While this is not thread safe, it's never going to be altered
        from a different thread and provides adquate convenience to warrant
        the small amount of risk around using cached_property.
        """
        return compute_file_hash(self._file_path)

    @property
    def schedule_data(self):
        return load_schedule(self._file_path)

    @property
    def has_schedule_changed(self):
        has_change = compute_file_hash(self._file_path) != self.last_hash
        if has_change:
            logger.info("Detected schedule change. Updating...")
            del self.last_hash
        return has_change

    def _loop(self):
        while not self._stop_event.is_set():
            if self.has_schedule_changed:
                self._on_change(self.schedule_data)
            if self._stop_event.wait(self._poll_interval):
                logger.info("Stop signal received for ScheduleMonitor. Stopping.")
                return

    def run(self):
        self._loop()

    def stop(self):
        self._stop_event.set()
        # we call self.join from the main thread


class CronRunner(Thread):
    def __init__(
        self, test_on_start: bool = False, block_interval: int = 2, daemon=True
    ):
        self._test_on_start = test_on_start
        self._stop_event = Event()
        self._schedule_updated = Event()
        self._queue: Queue = Queue()
        self._block_interval = block_interval
        self._current_schedule = None
        self._scheduler: Scheduler | None = None
        self._fire_time_delta = 0
        super().__init__(daemon=daemon)

        logger.info(
            f"CronRunner started with block interval of {block_interval} seconds."
        )

    def _run_once(self):
        try:
            if self._schedule_updated.is_set():
                new_schedule = self._queue.get_nowait()
                self._schedule_updated.clear()
                if new_schedule and new_schedule != self._current_schedule:
                    self._current_schedule = new_schedule
                    logger.info("Schedule has been updated.")
                    self._build_scheduler()
        except Empty:
            pass
        if self._scheduler:
            if self._scheduler.wait():
                logger.info("Scheduled wait operation was interrupted. Bypassing send.")
            else:
                self._scheduler.send()
        else:
            if self._stop_event.wait(self._block_interval):
                return

    def _loop(self):
        if self._test_on_start:
            from .scheduler import post_message

            post_message("Test message from notifier at " + datetime.now().ctime())
        while not self._stop_event.is_set():
            self._run_once()

    def _build_scheduler(self):
        if self._current_schedule is None:
            raise TypeError
        self._scheduler = Scheduler(
            schedule=self._current_schedule,
            stop_event=self._stop_event,
            schedule_updated_event=self._schedule_updated,
        )

    def stop(self):
        self._stop_event.set()
        self._schedule_updated.set()

    def update_schedule(self, new_schedule: dict):
        self._queue.put(new_schedule)
        self._schedule_updated.set()

    def run(self):
        self._loop()
