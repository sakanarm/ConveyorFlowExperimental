"""Explicit instrument amendment to the frozen youtube-dl preflight.

v1 stopped before constructing any container because its metadata filter was
3.8 while every frozen youtube-dl case declares 3.7. This version keeps the
case queue, executable image, tests, and selection rule unchanged; only the
metadata scope filter is set to 3.7. Actual execution remains CPython 3.8.20
and is disclosed as an environment deviation. No LLM calls are made here.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import qualify_youtube_dl_v1 as q

ORIGINAL_ROOT = q.ROOT
ORIGINAL_LOCK = q.LOCK
ROOT = q.HERE / "results/youtube_dl_preflight_v1b"
QUEUE = ROOT / "queue.json"
CONFIG = ROOT / "config.json"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"


def freeze():
    original = q.read(ORIGINAL_LOCK)
    if original["status"] != "v2_5_youtube_dl_preflight_frozen_no_provider_calls":
        raise ValueError("Original queue/lock was not frozen")
    if (ORIGINAL_ROOT / "ledger.jsonl").exists():
        raise ValueError("Original preflight unexpectedly started a container")
    old_queue = ORIGINAL_ROOT / "queue.json"
    old_config = ORIGINAL_ROOT / "config.json"
    if (original["queue_sha256"] != q.sha(old_queue)
            or original["config_sha256"] != q.sha(old_config)):
        raise ValueError("Original preflight evidence changed")
    config = q.read(old_config)
    if config["python_scope"] != "3.8" or not all(
            row["python_version"].startswith("3.7.")
            for row in q.read(old_queue)["candidates"]):
        raise ValueError("v1 metadata mismatch no longer present")
    config["python_scope"] = "3.7"
    config["status"] = "v2_5_youtube_dl_explicit_metadata_scope_amendment"
    stable = {
        "status": "v2_5_youtube_dl_preflight_v1b_frozen_no_provider_calls",
        "original_lock_sha256": q.sha(ORIGINAL_LOCK),
        "original_runner_sha256": q.sha(q.HERE / "qualify_youtube_dl_v1.py"),
        "amended_runner_sha256": q.sha(__file__),
        "original_preflight_failure": "Python version outside frozen scope before any container build",
        "actual_container_python": "3.8.20",
        "case_metadata_python_scope": "3.7",
        "queue_unchanged": True,
        "provider_calls": 0,
        "paid_execution_allowed": False,
    }
    if LOCK.exists():
        locked = q.read(LOCK)
        if (any(locked.get(key) != value for key, value in stable.items())
                or QUEUE.read_bytes() != old_queue.read_bytes()
                or q.read(CONFIG) != config
                or locked["queue_sha256"] != q.sha(QUEUE)
                or locked["config_sha256"] != q.sha(CONFIG)):
            raise ValueError("Amended preflight lock drift")
        return locked
    if ROOT.exists():
        raise FileExistsError("Partial amended preflight root exists")
    ROOT.mkdir(parents=True)
    QUEUE.write_bytes(old_queue.read_bytes())
    q.save_new(CONFIG, config)
    locked = {**stable, "queue_sha256": q.sha(QUEUE),
              "config_sha256": q.sha(CONFIG),
              "created_at_utc": datetime.now(timezone.utc).isoformat()}
    q.save_new(LOCK, locked)
    return locked


def install():
    q.ROOT, q.QUEUE, q.CONFIG, q.LOCK, q.LEDGER = ROOT, QUEUE, CONFIG, LOCK, LEDGER
    q.freeze = freeze


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--audit", action="store_true")
    group.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    install()
    result = q.run_next() if args.run_next else q.audit() if args.audit else {
        "status": freeze()["status"], "provider_calls": 0,
        "lock_sha256": q.sha(LOCK)}
    print(json.dumps(result, sort_keys=True))
