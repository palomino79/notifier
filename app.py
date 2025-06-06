import os
import signal
from threading import Event
from time import sleep
from notify.notify import CronRunner, ScheduleMonitor
from notify.vars import SCHEDULE_PATH, TOPIC, PUSH_SERVICE_URL, TEST_ON_START


def check_environment():
    must_be_set = "{} environment variable must be set."
    if not SCHEDULE_PATH:
        raise EnvironmentError(must_be_set.format("SCHEDULE_PATH"))
    if not PUSH_SERVICE_URL:
        raise EnvironmentError(must_be_set.format("PUSH_SERVICE_URL"))
    if not TOPIC:
        raise EnvironmentError(must_be_set.format("TOPIC"))
    if not os.path.exists(SCHEDULE_PATH):
        raise FileNotFoundError(f"SCHEDULE_PATH: {SCHEDULE_PATH} does not exist.")


def main():
    check_environment()
    stop_event = Event()

    def signal_handler(signum, frame):
        print(f"\n[main] Received signal {signum}. Shutting down...")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    cron = CronRunner(test_on_start=TEST_ON_START)
    monitor = ScheduleMonitor(SCHEDULE_PATH, cron.update_config)  # type: ignore
    cron.start()
    monitor.start()

    try:
        while not stop_event.is_set():
            sleep(1)
    except Exception:
        pass
    finally:
        monitor.stop()
        cron.stop()
        monitor.join()
        cron.join()


if __name__ == "__main__":
    main()
