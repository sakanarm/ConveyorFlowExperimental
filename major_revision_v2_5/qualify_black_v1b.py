"""Pre-provider Black environment amendment: add declared typing-extensions.

The original case 21 passed in both variants; case 3 could not collect in
either variant because the minimal image omitted a package listed in its
public requirements snapshot. Replay the same whole hash queue from index 0.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

import qualify_black_v1 as original

HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/black_preflight_v1b"
CONFIG = ROOT / "config.json"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"
sys.path.insert(0, str(HERE.parent / "major_revision_v2_3"))
import preflight_oci_v2 as engine  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, payload: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


def config_plan() -> dict:
    config = read(original.CONFIG)
    config["profiles"]["black"]["packages"].append("typing-extensions==3.7.4.1")
    config["environment_deviation"] += (
        " V1b adds typing-extensions==3.7.4.1 from the public bug-3 requirements "
        "after identical missing-import collection errors in both variants."
    )
    return config


def freeze() -> dict:
    old = original.audit()
    rows = original.records()
    if (old["attempted"] != 2 or len(rows) != 2 or
            [row["bug_id"] for row in rows] != ["21", "3"] or
            any(row["status"] != "environment_excluded" for row in rows)):
        raise ValueError("Original Black prefix changed")
    first = read(original.ROOT / "00_black_21/preflight_record.json")
    second = read(original.ROOT / "01_black_3/preflight_record.json")
    buggy = read(original.ROOT / "01_black_3/buggy/execution.json")
    fixed = read(original.ROOT / "01_black_3/fixed/execution.json")
    if (first["test_outcomes"]["buggy"]["return_code"] != 0 or
            first["test_outcomes"]["fixed"]["return_code"] != 0 or
            second["test_outcomes"]["buggy"]["return_code"] != 4 or
            second["test_outcomes"]["fixed"]["return_code"] != 4 or
            "No module named 'typing_extensions'" not in buggy["stdout"] or
            "No module named 'typing_extensions'" not in fixed["stdout"]):
        raise ValueError("Declared common import failure absent")
    stable = {
        "status": "v2_5_black_typing_extensions_amendment_frozen_before_provider",
        "original_queue_sha256": sha256(original.QUEUE),
        "original_config_sha256": sha256(original.CONFIG),
        "original_ledger_sha256": sha256(original.LEDGER),
        "original_case21_record_sha256": sha256(
            original.ROOT / "00_black_21/preflight_record.json"),
        "original_case3_record_sha256": sha256(
            original.ROOT / "01_black_3/preflight_record.json"),
        "runner_sha256": sha256(Path(__file__)),
        "engine_sha256": sha256(HERE / "preflight_oci_v2.py"),
        "rule": "Add only repository-declared missing package to common profile; replay original queue from zero",
        "provider_calls": 0, "paid_execution_allowed": False,
    }
    config = config_plan()
    if LOCK.exists():
        locked = read(LOCK)
        if (any(locked.get(key) != value for key, value in stable.items()) or
                read(CONFIG) != config or locked["config_sha256"] != sha256(CONFIG)):
            raise ValueError("Frozen Black v1b drift")
        return locked
    if ROOT.exists():
        raise FileExistsError("Black v1b root exists without lock")
    ROOT.mkdir(parents=True)
    save_new(CONFIG, config)
    locked = {**stable, "config_sha256": sha256(CONFIG),
              "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def records() -> list[dict]:
    return [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()] if LEDGER.exists() else []


def audit() -> dict:
    freeze()
    queue = read(original.QUEUE)["candidates"]
    rows = records()
    for index, row in enumerate(rows):
        item = queue[index]
        if (row["queue_index"] != index or row["bug_id"] != item["bug_id"] or
                row["selection_hash"] != item["selection_hash"]):
            raise ValueError("Amended Black ledger skipped a case")
        evidence = ROOT / f"{index:02d}_black_{item['bug_id']}" / "preflight_record.json"
        if sha256(evidence) != row["record_sha256"]:
            raise ValueError("Amended Black evidence drift")
    passed = [row["bug_id"] for row in rows if row["status"] == "reproducible"]
    return {
        "status": "first_case_qualified" if passed else
                  "queue_exhausted" if len(rows) == len(queue) else "preflight_incomplete",
        "attempted": len(rows), "first_qualified_bug_id": passed[0] if passed else None,
        "lock_sha256": sha256(LOCK), "provider_calls": 0,
        "paid_execution_allowed": False,
    }


def run_next() -> dict:
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    state = audit()
    if state["status"] != "preflight_incomplete":
        return state
    index = state["attempted"]
    case = read(original.QUEUE)["candidates"][index]
    out = ROOT / f"{index:02d}_black_{case['bug_id']}"
    print(json.dumps({"status": "black_amended_preflight_started",
                      "bug_id": case["bug_id"], "provider_calls": 0}), flush=True)
    record = engine.run_one(case, read(CONFIG), out)
    row = {
        "queue_index": index, "bug_id": case["bug_id"],
        "selection_hash": case["selection_hash"],
        "status": record["status"], "reason": record.get("reason"),
        "record_sha256": sha256(out / "preflight_record.json"),
        "provider_calls": 0,
    }
    with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--freeze", action="store_true")
    action.add_argument("--audit", action="store_true")
    action.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    result = run_next() if args.run_next else audit() if args.audit else {
        "status": freeze()["status"], "lock_sha256": sha256(LOCK),
        "provider_calls": 0,
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
