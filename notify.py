import requests
from yaml import load, Loader  # type: ignore
from typing import List
import json
import sys
import hashlib
import os
import time
import signal
from cron import collect_notification_times, get_next_time
from datetime import datetime
from notify_dates import NotifyDate, NotifyTimeAbsentError, DateAbsentError
from queue import Queue, Empty
from threading import Thread, Event
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(filename="notify.log")


SERVICE = os.environ.get("SERVICE", "ntfy")
TOPIC = os.environ.get("TOPIC", "birthday-alerts")


def get_file_hash(file_path: str):
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_file_data(file_path: str):
    with open(file_path, "r") as infile:
        res = load(infile, Loader)
        json.dump(res, sys.stdout, indent=4)


def build_notify_dates_list(data: dict):
    res = []
    for _, value in data.items():
        for _, item in value.items():
            res.append(NotifyDate(item))
    return res


def notify(nd: NotifyDate):
    title = nd.data.get("title")
    for_ = nd.data.get("for")
    date = nd.data.get("date")
    message = f"Upcoming reminder: {title}. For: {for_}. When: {date}"
    try:
        requests.post(f"http://{SERVICE}/{TOPIC}", data=message)
    except requests.HTTPError as e:
        print(e)


def check_firing_times(notify_dates: List[NotifyDate], trigger_times):
    for nd in notify_dates:
        for t in trigger_times:
            try:
                if nd.should_notify(t):
                    notify(nd)
                    break
            except NotifyTimeAbsentError:
                logger.error(f"No notify_time set for notify_date {nd.title}")
            except DateAbsentError:
                logger.error(f"No date set for notify_date {nd.title}")
            except ValueError as e:
                logger.error(e, exc_info=True)


def monitor_config(q: Queue, config_updated: Event, stop_event: Event):
    yml_path = "notify.yml"
    last_hash = get_file_hash(yml_path)
    file_data = get_file_data(yml_path)
    while not stop_event.is_set():
        this_hash = get_file_hash(yml_path)
        if this_hash != last_hash:
            file_data = get_file_data(yml_path)
            q.put(file_data)
            config_updated.set()
            last_hash = this_hash
        stop_event.wait(timeout=3)


def run_cron(q: Queue, config_updated: Event, stop_event: Event, initial_config: dict):
    file_data = initial_config
    trigger_times = collect_notification_times(file_data)
    time_generator = get_next_time(trigger_times)
    notify_dates = build_notify_dates_list(file_data)
    while not stop_event.is_set():
        try:
            new_data = q.get(timeout=3)
        except Empty:
            pass
        else:
            file_data = new_data
            trigger_times = collect_notification_times(file_data)
            time_generator = get_next_time(trigger_times)
            notify_dates = build_notify_dates_list(file_data)
        if notify_dates and time_generator:
            next_time = next(time_generator)
            until_next_time = max((next_time - datetime.now()).total_seconds(), 0)
            timed_out = config_updated.wait(until_next_time) or stop_event.is_set()
            if not timed_out:
                config_updated.clear()
            check_firing_times(notify_dates, trigger_times)


def main():
    q = Queue()  # type: ignore
    stop_event = Event()
    config_updated = Event()

    def signal_handler(signum, frame):
        print(f"\n[main] Received signal {signum}. Shutting down...")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    yml_path = "notify.yml"
    initial_config = get_file_data(yml_path)
    mc = Thread(target=monitor_config, args=(q, config_updated, stop_event))
    rc = Thread(target=run_cron, args=(q, config_updated, stop_event, initial_config))
    mc.start()
    rc.start()

    try:
        while not stop_event.is_set():
            time.sleep(1)
    except Exception:
        stop_event.set()
    mc.join()
    rc.join()


if __name__ == "__main__":
    main()
