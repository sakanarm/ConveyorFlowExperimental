"""Pre-provider dependency amendment for all frozen PySnooper candidates.

V1 failed before tests on an invalid OCI tag. V1b built but both variants
failed collection because the repository-declared python_toolbox test extra
was absent. V1c adds its published minimum version and replays the full queue.
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
import qualify_pysnooper_v1b as prior

HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/pysnooper_preflight_v1c"
CONFIG = ROOT / "config.json"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"
sys.path.insert(0, str(HERE.parent / "major_revision_v2_3"))
import preflight_oci_v2 as engine  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def expected_config() -> dict:
    config = read(original.CONFIG)
    config["profiles"]["PySnooper"]["packages"].append("python_toolbox==0.9.3")
    config["environment_deviation"] += (
        " V1c adds repository-declared python_toolbox>=0.9.3 pinned at 0.9.3 "
        "after v1b failed test collection on both buggy and fixed."
    )
    return config


def freeze() -> dict:
    original.audit()
    state = prior.audit()
    rows = prior.records()
    if (state["attempted"] != 1 or len(rows) != 1 or rows[0]["bug_id"] != "3" or
            rows[0]["status"] != "environment_excluded"):
        raise ValueError("Prior amended instrument state changed")
    artifact = prior.ROOT / "00_pysnooper_3"
    record = read(artifact / "preflight_record.json")
    buggy = read(artifact / "buggy/execution.json")
    fixed = read(artifact / "fixed/execution.json")
    if (record["test_outcomes"]["buggy"]["return_code"] != 4 or
            record["test_outcomes"]["fixed"]["return_code"] != 4 or
            "No module named 'python_toolbox'" not in buggy["stdout"] or
            "No module named 'python_toolbox'" not in fixed["stdout"]):
        raise ValueError("Declared dependency failure not found in both variants")
    stable = {
        "status": "v2_5_pysnooper_test_dependency_amendment_frozen_before_provider",
        "source_queue_sha256": sha256(original.QUEUE),
        "source_config_sha256": sha256(original.CONFIG),
        "v1b_lock_sha256": sha256(prior.LOCK),
        "v1b_failure_record_sha256": sha256(artifact / "preflight_record.json"),
        "repository_declared_test_requirement": "python_toolbox>=0.9.3 in /buggy/test_requirements.txt of the v1b validator image",
        "v1b_validator_image_id": record["container_image_id"],
        "runner_sha256": sha256(Path(__file__)),
        "engine_sha256": sha256(HERE / "preflight_oci_v2.py"),
        "rule": "Add only the repository-declared missing test extra; replay all candidates from frozen queue start",
        "provider_calls": 0, "paid_execution_allowed": False,
    }
    config = expected_config()
    if LOCK.exists():
        lock = read(LOCK)
        if (any(lock.get(key) != value for key, value in stable.items()) or
                read(CONFIG) != config or lock["config_sha256"] != sha256(CONFIG)):
            raise ValueError("Frozen v1c protocol drift")
        return lock
    if ROOT.exists():
        raise FileExistsError("V1c root exists without lock")
    ROOT.mkdir(parents=True)
    save_new(CONFIG, config)
    lock = {**stable, "config_sha256": sha256(CONFIG),
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
        case = queue[index]
        if (row["queue_index"] != index or row["bug_id"] != case["bug_id"] or
                row["selection_hash"] != case["selection_hash"]):
            raise ValueError("V1c ledger skipped or reordered a case")
        evidence = ROOT / f"{index:02d}_pysnooper_{case['bug_id']}" / "preflight_record.json"
        if sha256(evidence) != row["record_sha256"]:
            raise ValueError("V1c preflight evidence drift")
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
    out = ROOT / f"{index:02d}_pysnooper_{case['bug_id']}"
    print(json.dumps({"status": "dependency_amended_preflight_started",
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
        "status": freeze()["status"], "lock_sha256": sha256(LOCK), "provider_calls": 0,
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
