"""Pre-provider PySnooper profile amendment using its own requirements.txt.

V1c reached collection in both variants but missed `future`. The buggy
repository declares decorator, future, and six; all are pinned here and
every case is replayed from the same frozen queue, regardless of outcome.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

import qualify_pysnooper_v1 as original
import qualify_pysnooper_v1c as prior

HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/pysnooper_preflight_v1d"
CONFIG = ROOT / "config.json"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"
sys.path.insert(0, str(HERE.parent / "major_revision_v2_3"))
import preflight_oci_v2 as engine  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, data: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")


def config_plan() -> dict:
    config = read(prior.CONFIG)
    config["profiles"]["PySnooper"]["packages"].extend([
        "decorator==4.4.2", "future==0.18.2", "six==1.15.0",
    ])
    config["environment_deviation"] += (
        " V1d pins all three project-declared runtime requirements: "
        "decorator>=4.3.0, future>=0.17.1, six>=1.12.0."
    )
    return config


def freeze() -> dict:
    state = prior.audit()
    rows = prior.records()
    if (state["attempted"] != 1 or len(rows) != 1 or rows[0]["bug_id"] != "3" or
            rows[0]["status"] != "environment_excluded"):
        raise ValueError("V1c prior state changed")
    artifact = prior.ROOT / "00_pysnooper_3"
    buggy = read(artifact / "buggy/execution.json")
    fixed = read(artifact / "fixed/execution.json")
    if ("No module named 'future'" not in buggy["stdout"] or
            "No module named 'future'" not in fixed["stdout"]):
        raise ValueError("Declared shared import failure absent")
    stable = {
        "status": "v2_5_pysnooper_runtime_requirements_amendment_frozen_before_provider",
        "source_queue_sha256": sha256(original.QUEUE),
        "v1c_lock_sha256": sha256(prior.LOCK),
        "v1c_failure_record_sha256": sha256(artifact / "preflight_record.json"),
        "v1c_config_sha256": sha256(prior.CONFIG),
        "v1c_validator_image_id": read(artifact / "preflight_record.json")["container_image_id"],
        "repository_declared_runtime_requirements": [
            "decorator>=4.3.0", "future>=0.17.1", "six>=1.12.0",
        ],
        "runner_sha256": sha256(Path(__file__)),
        "engine_sha256": sha256(HERE / "preflight_oci_v2.py"),
        "rule": "Add all project-declared runtime requirements to both variants; replay frozen queue from index zero",
        "provider_calls": 0, "paid_execution_allowed": False,
    }
    config = config_plan()
    if LOCK.exists():
        locked = read(LOCK)
        if (any(locked.get(key) != value for key, value in stable.items()) or
                read(CONFIG) != config or locked["config_sha256"] != sha256(CONFIG)):
            raise ValueError("Frozen v1d protocol drift")
        return locked
    if ROOT.exists():
        raise FileExistsError("V1d root exists without lock")
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
        case = queue[index]
        if (row["queue_index"] != index or row["bug_id"] != case["bug_id"] or
                row["selection_hash"] != case["selection_hash"]):
            raise ValueError("V1d ledger skipped or reordered a case")
        evidence = ROOT / f"{index:02d}_pysnooper_{case['bug_id']}" / "preflight_record.json"
        if sha256(evidence) != row["record_sha256"]:
            raise ValueError("V1d evidence drift")
    qualified = [row["bug_id"] for row in rows if row["status"] == "reproducible"]
    return {
        "status": "first_case_qualified" if qualified else
                  "queue_exhausted" if len(rows) == len(queue) else "preflight_incomplete",
        "attempted": len(rows), "first_qualified_bug_id": qualified[0] if qualified else None,
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
    out = ROOT / f"{index:02d}_pysnooper_{case['bug_id']}"
    print(json.dumps({"status": "runtime_amended_preflight_started",
                      "bug_id": case["bug_id"], "provider_calls": 0}), flush=True)
    record = engine.run_one(case, read(CONFIG), out)
    row = {
        "queue_index": index, "bug_id": case["bug_id"],
        "selection_hash": case["selection_hash"],
        "status": record["status"], "reason": record.get("reason"),
        "record_sha256": sha256(out / "preflight_record.json"), "provider_calls": 0,
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
