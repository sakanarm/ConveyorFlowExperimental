"""Qualify Sanic repair sources in frozen v2.6 order without LLM calls.

Keep every tried case, including failed builds/tests. Stop only after two
reproducible cases or exhaustion of the five-case unexposed project queue.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

from build_prior_exposure_ledger_v1 import HERE, MANIFEST
from build_unexposed_candidate_queue_v1 import OUTPUT as SOURCE_QUEUE

V2 = HERE.parent
ENGINE_DIR = V2 / "major_revision_v2_5"
sys.path.insert(0, str(V2 / "major_revision_v2_3"))
sys.path.insert(0, str(ENGINE_DIR))
import preflight_oci_v2 as engine  # noqa: E402

PROFILE = ENGINE_DIR / "results/sanic_preflight_v1/config.json"
ROOT = HERE / "sanic_preflight_v1"
QUEUE, CONFIG, LOCK, LEDGER = (ROOT / name for name in
                               ("queue.json", "config.json", "lock.json", "ledger.jsonl"))
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/sanic_preflight_v1"
RAW = (Path("D:/ConveyorFlowRuntime/v2_6/sanic_preflight_v1")
       if os.name == "nt" else Path(RAW_TEXT))


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write("\n")


def plans():
    source = read(SOURCE_QUEUE)
    if source["status"] != "metadata_queue_not_preflighted_not_main_cohort":
        raise ValueError("Unfrozen source queue")
    project = next(row for row in source["projects"] if row["project"] == "sanic")
    frame = [row for row in project["cases_in_frozen_hash_order"]
             if not row["prior_provider_exposure"]]
    candidates = {f"{row['project']}_{row['bug_id']}": row
                  for row in read(MANIFEST)["candidates"]}
    queue = []
    for row in frame:
        case = dict(candidates[row["case_id"]])
        case["selection_hash"] = row["case_order_sha256"]
        queue.append(case)
    if len(queue) != 5 or [f"sanic_{row['bug_id']}" for row in queue] != [
            row["case_id"] for row in frame]:
        raise ValueError("Sanic queue mismatch")
    config = read(PROFILE)
    if config["python_scope"] != "3.8" or list(config["profiles"]) != ["sanic"]:
        raise ValueError("Unexpected Sanic verifier profile")
    config["status"] = "v2_6_project_eligibility_preflight_only"
    config["environment_deviation"] += (
        " Reused generic engine OCI tag ends with v2.5; v2.6 case hashes, "
        "lock and raw directory identify this separate preflight.")
    return queue, config


def freeze():
    queue, config = plans()
    expected = {
        "status": "frozen_before_v2_6_sanic_container_preflight",
        "source_queue_sha256": sha(SOURCE_QUEUE),
        "manifest_sha256": sha(MANIFEST),
        "runner_sha256": sha(Path(__file__)),
        "engine_sha256": sha(ENGINE_DIR / "preflight_oci_v2.py"),
        "profile_source_sha256": sha(PROFILE),
        "raw_root": RAW_TEXT,
        "selection_rule": "First two reproducible in frozen case order; all exclusions logged",
        "provider_calls": 0,
        "paid_execution_allowed": False,
    }
    if LOCK.exists():
        lock = read(LOCK)
        if (any(lock.get(key) != value for key, value in expected.items())
                or read(QUEUE) != queue or read(CONFIG) != config
                or lock["queue_sha256"] != sha(QUEUE)
                or lock["config_sha256"] != sha(CONFIG)):
            raise ValueError("Sanic preflight lock drift")
        return lock
    if ROOT.exists():
        raise FileExistsError("Partial Sanic preflight root")
    ROOT.mkdir()
    save_new(QUEUE, queue)
    save_new(CONFIG, config)
    lock = {**expected, "queue_sha256": sha(QUEUE),
            "config_sha256": sha(CONFIG),
            "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, lock)
    return lock


def audit():
    freeze()
    queue = read(QUEUE)
    rows = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()] if LEDGER.exists() else []
    if len(rows) > len(queue):
        raise ValueError("Too many Sanic preflight attempts")
    for index, row in enumerate(rows):
        case = queue[index]
        record = RAW / f"{index:02d}_sanic_{case['bug_id']}/preflight_record.json"
        if (row["queue_index"] != index or row["case_id"] != f"sanic_{case['bug_id']}"
                or row["selection_hash"] != case["selection_hash"]
                or row["record_sha256"] != sha(record)):
            raise ValueError("Sanic case/evidence mismatch")
    good = [row["case_id"] for row in rows if row["status"] == "reproducible"]
    return {"status": "two_cases_qualified" if len(good) == 2 else
            "project_ineligible" if len(rows) == len(queue) else "preflight_incomplete",
            "attempted": len(rows), "queue_size": len(queue),
            "qualified_cases": good, "provider_calls": 0, "lock_sha256": sha(LOCK)}


def run_next():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    state = audit()
    if state["status"] != "preflight_incomplete":
        return state
    index = state["attempted"]
    case = read(QUEUE)[index]
    out = RAW / f"{index:02d}_sanic_{case['bug_id']}"
    out.parent.mkdir(parents=True, exist_ok=True)
    print(json.dumps({"status": "preflight_started", "case_id":
                      f"sanic_{case['bug_id']}", "provider_calls": 0}), flush=True)
    record = engine.run_one(case, read(CONFIG), out)
    row = {"queue_index": index, "case_id": f"sanic_{case['bug_id']}",
           "selection_hash": case["selection_hash"], "status": record["status"],
           "reason": record.get("reason"), "record_sha256": sha(out / "preflight_record.json"),
           "provider_calls": 0}
    with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--audit", action="store_true")
    mode.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    result = run_next() if args.run_next else audit() if args.audit else {
        "status": freeze()["status"], "lock_sha256": sha(LOCK), "provider_calls": 0}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
