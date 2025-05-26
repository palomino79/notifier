import requests
from yaml import load, Loader  # type: ignore
from typing import List
import json
import sys
import hashlib
from cron import collect_notification_times, get_next_time
from datetime import timedelta, datetime
from time import sleep
from notify_dates import NotifyDate


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
    pass


def check_firing_times(notify_dates: List[NotifyDate], trigger_times):
    for nd in notify_dates:
        for t in trigger_times:
            if nd.should_notify(t):
                notify(nd)
                break


"""
Realistically, there should be two threads. One watches for changes
to the configuration and then reinitializes the other thread with new
values. And the other thread actually controlling the cronjob and 
execution of behavior.
"""


def main():
    yml_path = "notify.yml"
    last_hash = get_file_hash(yml_path)
    file_data = get_file_data(yml_path)

    trigger_times = collect_notification_times(file_data)
    time_generator = get_next_time(trigger_times)
    while True:
        this_hash = get_file_hash(yml_path)
        if this_hash != last_hash:
            file_data = get_file_data(yml_path)
            trigger_times = collect_notification_times(file_data)
            time_generator = get_next_time(trigger_times)

        next_time = next(time_generator)
        until_next_time = next_time - datetime.now()
        sleep(until_next_time.seconds)


if __name__ == "__main__":
    main()
