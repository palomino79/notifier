import os
import time
import threading
import pytest
from pathlib import Path
from queue import Queue
from threading import Event

import notify  # replace with the actual import path where ConfigMonitor lives
from notify import ConfigMonitor, compute_file_hash, load_config


@pytest.fixture
def tmp_yaml(tmp_path):
    """
    Create a temporary YAML file with some initial content and return its path.
    """
    file_path = tmp_path / "config.yml"
    initial_data = {
        "group1": {
            "item1": {
                "title": "foo",
                "for_": "bar",
                "date": "January 01",
                "notify_time": "09:00 AM",
                "notify_before_days": 0,
            }
        }
    }
    # Write it out as YAML
    import yaml

    file_path.write_text(yaml.safe_dump(initial_data))
    return str(file_path)


def test_compute_file_hash_and_load_config(tmp_yaml):
    # compute_file_hash should match the hash of the actual file
    h1 = compute_file_hash(tmp_yaml)
    # writing the same data again should give the same hash
    h2 = compute_file_hash(tmp_yaml)
    assert h1 == h2

    # load_config should return a dict with our initial content
    cfg = load_config(tmp_yaml)
    assert isinstance(cfg, dict)
    assert "group1" in cfg
    assert "item1" in cfg["group1"]
    assert cfg["group1"]["item1"]["title"] == "foo"


def test_has_config_changed_property(tmp_yaml):
    # Create a monitor but do not start its thread; test has_config_changed directly
    monitor = ConfigMonitor(
        tmp_yaml, on_change=lambda x: None, poll_interval=0.01, daemon=False
    )

    # Initially, nothing has changed
    assert monitor.has_config_changed is False

    # Modify the file on disk
    time.sleep(0.01)  # ensure filesystem mtime update
    with open(tmp_yaml, "w") as f:
        f.write("group2:\n  item2:\n    title: baz\n")  # minimal valid YAML

    # After rewriting, last_hash should be updated internally
    assert monitor.has_config_changed is True

    # Calling has_config_changed a second time should now return False (because last_hash was updated)
    assert monitor.has_config_changed is False


def test_run_calls_on_change_when_file_updates(tmp_yaml):
    # Arrange: a small YAML and a callback that captures calls
    called = []

    def on_change_callback(new_cfg):
        called.append(new_cfg)

    monitor = ConfigMonitor(
        tmp_yaml, on_change=on_change_callback, poll_interval=0.01, daemon=True
    )
    monitor.start()

    # Wait a moment for the thread to start
    time.sleep(0.02)

    # Overwrite the file so that has_config_changed becomes True
    with open(tmp_yaml, "w") as f:
        f.write("groupX:\n  itemY:\n    title: newval\n")  # new content

    # Give the monitor thread enough time to detect the change
    time.sleep(0.05)

    # We expect on_change_callback to have been called once with the new dict
    assert len(called) >= 1
    assert isinstance(called[0], dict)
    assert "groupX" in called[0]
    assert called[0]["groupX"]["itemY"]["title"] == "newval"

    # Clean up
    monitor.stop()
    monitor.join()


def test_stop_prevents_further_on_change(tmp_yaml):
    called = []

    def on_change_callback(new_cfg):
        called.append(new_cfg)

    monitor = ConfigMonitor(
        tmp_yaml, on_change=on_change_callback, poll_interval=0.01, daemon=True
    )
    monitor.start()
    time.sleep(0.02)

    # First change
    with open(tmp_yaml, "w") as f:
        f.write("a: 1\n")
    time.sleep(0.05)
    assert len(called) >= 1

    # Now stop the monitor
    monitor.stop()
    time.sleep(0.01)

    # Make another change to the file
    with open(tmp_yaml, "w") as f:
        f.write("b: 2\n")
    time.sleep(0.05)

    # After stopping, on_change should not be called again
    assert len(called) == 1

    monitor.join()
