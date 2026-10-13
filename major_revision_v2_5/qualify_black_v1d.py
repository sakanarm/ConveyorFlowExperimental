"""Pre-provider Black amendment: install its declared blackd optional extras.

V1c reached the public test module but both historical variants failed at
collection because AioHTTPTestCase was undefined. Replay the original queue.
"""

from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import qualify_black_v1 as original
import qualify_black_v1c as previous
import preflight_oci_v2 as engine


HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/black_preflight_v1d"
CONFIG = ROOT / "config.json"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def freeze() -> dict:
    old = previous.audit()
    rows = previous.records()
    if (old["attempted"] != 2 or [r["bug_id"] for r in rows] != ["21", "3"] or
            any(r["status"] != "environment_excluded" for r in rows)):
        raise ValueError("Prior Black queue prefix changed")
    records = [read(previous.ROOT / f"{i:02d}_black_{bug}/preflight_record.json")
               for i, bug in enumerate((21, 3))]
    buggy = read(previous.ROOT / "01_black_3/buggy/execution.json")
    fixed = read(previous.ROOT / "01_black_3/fixed/execution.json")
    if (records[0]["test_outcomes"]["buggy"]["return_code"] != 0 or
            records[0]["test_outcomes"]["fixed"]["return_code"] != 0 or
            records[1]["test_outcomes"]["buggy"]["return_code"] != 4 or
            records[1]["test_outcomes"]["fixed"]["return_code"] != 4 or
            "AioHTTPTestCase' is not defined" not in buggy["stdout"] or
            "AioHTTPTestCase' is not defined" not in fixed["stdout"]):
        raise ValueError("Symmetric declared optional dependency failure absent")
    config = read(previous.CONFIG)
    config["profiles"]["black"]["packages"].extend((
        "aiohttp==3.8.6", "aiohttp-cors==0.7.0"))
    config["environment_deviation"] += (
        " V1d adds the blackd optional extra dependencies declared in Black"
        " setup.py (aiohttp>=3.3.2 and aiohttp-cors), pinned to Python-3.8"
        " compatible releases after a symmetric public-test collection failure."
        " The original case order and test nodes are unchanged."
    )
    stable = {
        "status": "v2_5_black_declared_blackd_extra_amendment_frozen_before_provider",
        "original_queue_sha256": sha(original.QUEUE),
        "previous_lock_sha256": sha(previous.LOCK),
        "previous_ledger_sha256": sha(previous.LEDGER),
        "previous_case21_record_sha256": sha(previous.ROOT / "00_black_21/preflight_record.json"),
        "previous_case3_record_sha256": sha(previous.ROOT / "01_black_3/preflight_record.json"),
        "runner_sha256": sha(Path(__file__)), "engine_sha256": sha(HERE / "preflight_oci_v2.py"),
        "rule": "Install declared blackd extras in both variants; replay original queue from zero",
        "dependency_urls": ["https://pypi.org/project/aiohttp/3.8.6/",
                            "https://pypi.org/project/aiohttp-cors/0.7.0/"],
        "provider_calls": 0, "paid_execution_allowed": False,
    }
    if LOCK.exists():
        lock = read(LOCK)
        if (any(lock.get(key) != value for key, value in stable.items()) or
                lock["config_sha256"] != sha(CONFIG) or read(CONFIG) != config):
            raise ValueError("Frozen Black v1d drift")
        return lock
    if ROOT.exists():
        raise FileExistsError("Black v1d root exists without lock")
    ROOT.mkdir(parents=True)
    save_new(CONFIG, config)
    lock = {**stable, "config_sha256": sha(CONFIG),
            "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, lock)
    return lock


def records() -> list[dict]:
    return [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()] if LEDGER.exists() else []


def audit() -> dict:
    freeze()
    queue = read(original.QUEUE)["candidates"]
    rows = records()
    for index, row in enumerate(rows):
        item = queue[index]
        evidence = ROOT / f"{index:02d}_black_{item['bug_id']}/preflight_record.json"
        if (row["queue_index"] != index or row["bug_id"] != item["bug_id"] or
                row["selection_hash"] != item["selection_hash"] or
                row["record_sha256"] != sha(evidence)):
            raise ValueError("Black v1d queue/evidence drift")
    passed = [row["bug_id"] for row in rows if row["status"] == "reproducible"]
    return {"status": "first_case_qualified" if passed else
            "queue_exhausted" if len(rows) == len(queue) else "preflight_incomplete",
            "attempted": len(rows), "first_qualified_bug_id": passed[0] if passed else None,
            "provider_calls": 0, "lock_sha256": sha(LOCK)}


def run_next() -> dict:
    if (sys.platform != "linux" or os.geteuid() != 0 or
            os.environ.get("CONVEYORFLOW_CONTAINER_COMMAND") != "podman"):
        raise ValueError("Rootful Linux/Podman required")
    state = audit()
    if state["status"] != "preflight_incomplete":
        return state
    index = state["attempted"]
    item = read(original.QUEUE)["candidates"][index]
    out = ROOT / f"{index:02d}_black_{item['bug_id']}"
    print(json.dumps({"event": "black_v1d_preflight_started", "index": index,
                      "bug_id": item["bug_id"], "provider_calls": 0}), flush=True)
    record = engine.run_one(item, read(CONFIG), out)
    row = {"queue_index": index, "bug_id": item["bug_id"],
           "selection_hash": item["selection_hash"], "status": record["status"],
           "reason": record.get("reason"), "record_sha256": sha(out / "preflight_record.json"),
           "provider_calls": 0}
    with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    return row


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    action = cli.add_mutually_exclusive_group(required=True)
    action.add_argument("--freeze", action="store_true")
    action.add_argument("--audit", action="store_true")
    action.add_argument("--run-next", action="store_true")
    args = cli.parse_args()
    result = run_next() if args.run_next else audit() if args.audit else {
        "status": freeze()["status"], "provider_calls": 0}
    print(json.dumps(result, sort_keys=True))
