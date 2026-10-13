"""Outcome-blind Black repository buggy/fixed container qualification.

The historical unittest selector is mapped mechanically to the same pytest
class/method node by preflight_oci_v2. Mixed-file metadata is excluded before
any test result, not silently coerced into a single-file case.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys


HERE = Path(__file__).resolve().parent
V2 = HERE.parent
PREVIOUS = V2 / "major_revision_v2_3"
SOURCE = PREVIOUS / "bugsinpy_candidate_manifest.json"
ROOT = HERE / "results/black_preflight_v1"
QUEUE = ROOT / "queue.json"
CONFIG = ROOT / "config.json"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"
DOMAIN = "ConveyorFlow-v2.5-new-project-black-20261011"
QUEUE_LENGTH = 8

sys.path.insert(0, str(PREVIOUS))
import preflight_oci_v2 as engine  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def queue_plan() -> dict:
    eligible, exclusions = [], []
    for item in read(SOURCE)["candidates"]:
        if item["project"] != "black" or not item["python_version"].startswith("3.8."):
            continue
        bug_id = str(item["bug_id"])
        metadata = V2 / "bip/projects/black/bugs" / bug_id
        if (sha256(metadata / "bug.info") != item["bug_info_sha256"] or
                sha256(metadata / "run_test.sh") != item["run_test_sha256"]):
            raise ValueError("Black public metadata drift")
        command = shlex.split((metadata / "run_test.sh").read_text(encoding="utf-8"))
        test_file = item["test_file"]
        stem = test_file[:-3].replace("/", ".") if test_file.endswith(".py") else ""
        if (";" in test_file or not stem or len(command) != 5 or
                command[:4] != ["python", "-m", "unittest", "-q"] or
                not command[4].startswith(stem + ".")):
            exclusions.append({"bug_id": bug_id, "reason": "unsupported multi-file or non-unittest public selector"})
            continue
        eligible.append(item)
    eligible.sort(key=lambda item: hashlib.sha256(
        f"{DOMAIN}|black|{item['bug_id']}".encode("utf-8")).hexdigest())
    if len(eligible) < QUEUE_LENGTH:
        raise ValueError("Fewer than eight metadata-qualified Black cases")
    return {
        "status": "metadata_only_not_preflighted",
        "selection_domain": DOMAIN,
        "rule": "First buggy-fail/fixed-pass in first eight supported cases sorted by salted case hash; retain every failed preflight",
        "candidates": eligible[:QUEUE_LENGTH],
        "metadata_exclusions": sorted(exclusions, key=lambda item: int(item["bug_id"])),
        "provider_calls": 0,
    }


def config_plan() -> dict:
    base = read(PREVIOUS / "config_bugsinpy_preflight_v2.json")
    base["max_candidates"] = QUEUE_LENGTH
    base["profiles"] = {
        "black": {
            "url": "https://github.com/psf/black",
            "packages": [
                "pytest==5.4.3", "click==7.1.1", "attrs==19.3.0",
                "appdirs==1.4.3", "toml==0.10.0", "pathspec==0.7.0",
                "regex==2020.4.4", "typed-ast==1.4.1",
                "mypy-extensions==0.4.3",
            ],
            "build": "true",
        },
    }
    base["environment_deviation"] = (
        "Black feasibility on CPython 3.8.20 with pinned minimal packages "
        "drawn from the public benchmark requirements. Historical unittest "
        "class/method is run as the corresponding pytest node. Not exact "
        "historical environment; both variants use identical test runner."
    )
    return base


def freeze() -> dict:
    queue, config = queue_plan(), config_plan()
    stable = {
        "status": "v2_5_black_preflight_frozen_no_provider_calls",
        "source_manifest_sha256": sha256(SOURCE),
        "runner_sha256": sha256(Path(__file__)),
        "engine_sha256": sha256(HERE / "preflight_oci_v2.py"),
        "base_config_sha256": sha256(PREVIOUS / "config_bugsinpy_preflight_v2.json"),
        "provider_calls": 0, "paid_execution_allowed": False,
    }
    if LOCK.exists():
        lock = read(LOCK)
        if (any(lock.get(key) != value for key, value in stable.items()) or
                read(QUEUE) != queue or read(CONFIG) != config or
                lock["queue_sha256"] != sha256(QUEUE) or
                lock["config_sha256"] != sha256(CONFIG)):
            raise ValueError("Frozen Black queue/profile drift")
        return lock
    if ROOT.exists():
        raise FileExistsError("Black preflight root exists without lock")
    ROOT.mkdir(parents=True)
    save_new(QUEUE, queue)
    save_new(CONFIG, config)
    lock = {**stable, "queue_sha256": sha256(QUEUE),
            "config_sha256": sha256(CONFIG),
            "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, lock)
    return lock


def records() -> list[dict]:
    return [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()] if LEDGER.exists() else []


def audit() -> dict:
    freeze()
    queue = read(QUEUE)["candidates"]
    rows = records()
    for index, row in enumerate(rows):
        case = queue[index]
        if (row["queue_index"] != index or row["bug_id"] != case["bug_id"] or
                row["selection_hash"] != case["selection_hash"]):
            raise ValueError("Black preflight ledger skipped a case")
        proof = ROOT / f"{index:02d}_black_{case['bug_id']}" / "preflight_record.json"
        if sha256(proof) != row["record_sha256"]:
            raise ValueError("Black preflight evidence drift")
    passed = [row["bug_id"] for row in rows if row["status"] == "reproducible"]
    return {
        "status": "first_case_qualified" if passed else
                  "queue_exhausted" if len(rows) == len(queue) else "preflight_incomplete",
        "attempted": len(rows), "queue_size": len(queue),
        "first_qualified_bug_id": passed[0] if passed else None,
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
    case = read(QUEUE)["candidates"][index]
    out = ROOT / f"{index:02d}_black_{case['bug_id']}"
    print(json.dumps({"status": "black_container_preflight_started",
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
