import hashlib
import logging
from datetime import datetime, timedelta
from typing import Callable
from queue import Queue, Empty
from threading import Thread, Event
from functools import cached_property
from yaml import load, Loader  # type: ignore
from .scheduler import Scheduler
from .notify_dates import NotifyDate
from .vars import TIMEZONE

logger = logging.getLogger(__name__)
logging.basicConfig()


def compute_file_hash(file_path: str):
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def load_config(file_path: str):
    with open(file_path, "r") as infile:
        res = load(infile, Loader)
        return res


class ConfigMonitor(Thread):
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
        self._stop = Event()
        self._last_hash = compute_file_hash(file_path)
        super().__init__(daemon=daemon)

    @cached_property
    def last_hash(self):
        """
        While this is not thread safe, it's never going to be altered
        from a different thread and provides adquate convenience to warrant
        the small amount of risk around using cached_property.
        """
        return compute_file_hash(self._file_path)

    @property
    def config_data(self):
        return load_config(self._file_path)

    @property
    def has_config_changed(self):
        has_change = compute_file_hash(self._file_path) != self.last_hash
        if has_change:
            del self.last_hash
        return has_change

    def _loop(self):
        while not self._stop.is_set():
            if self.has_config_changed:
                self._on_change(self.config_data)
            if self._stop.wait(self._poll_interval):
                return

    def run(self):
        self._loop()

    def stop(self):
        self._stop.set()
        # we call self.join from the main thread


class CronRunner(Thread):
    def __init__(self, block_interval: int = 2, daemon=True):
        self._stop = Event()
        self._config_updated = Event()
        self._queue: Queue = Queue()
        self._block_interval = block_interval
        self._current_config = None
        self._scheduler: Scheduler | None = None
        self._fire_time_delta = 0
        super().__init__(daemon=daemon)

    @property
    def fire_time_generator(self):
        while True:
            for t in self.fire_times:
                now = datetime.now(tz=TIMEZONE)
                if t > now:
                    yield t
            self._fire_time_delta += 1
            if self._scheduler:
                self._scheduler.fire_times = self.fire_times

    @property
    def fire_times(self):
        now = datetime.now(tz=TIMEZONE)
        times = []
        if not self._current_config:
            return []
        for value in self._current_config.values():
            for item in value.values():
                time = item.get("notify_time")
                if not time:
                    logger.warning("No time found. Continuing.")
                    continue
                temp = datetime.strptime(time, "%I:%M %p").time()
                dt = now.replace(
                    hour=temp.hour, minute=temp.minute, second=0, microsecond=0
                )
                times.append(dt + timedelta(days=self._fire_time_delta))
        times = list(set(times))
        return sorted(times)

    @property
    def notify_dates(self):
        if not self._current_config:
            return []
        return [
            NotifyDate(x)
            for item in self._current_config.values()
            for x in item.values()
        ]

    def _run_once(self):
        try:
            if self._config_updated.is_set():
                new_config = self._queue.get_nowait()
                self._config_updated.clear()
        except Empty:
            new_config = None
        else:
            if new_config and new_config != self._current_config:
                self._current_config = new_config
                self._build_scheduler()
        if self._scheduler:
            # .wait() blocks until we need to send again
            self._scheduler.wait()
            self._scheduler.send()
        else:
            if self._stop.wait(self._block_interval):
                return

    def _loop(self):
        while not self._stop.is_set():
            self._run_once()

    def _build_scheduler(self):
        if self._current_config is None:
            raise TypeError
        self._scheduler = Scheduler(
            notify_dates=self.notify_dates,
            fire_times=self.fire_times,
            time_generator=self.fire_time_generator,
            stop_event=self._stop,
            config_updated_event=self._config_updated,
        )

    def stop(self):
        self._stop.set()
        self._config_updated.set()

    def update_config(self, new_config: dict):
        self._queue.put(new_config)
        self._config_updated.set()

    def run(self):
        self._loop()
