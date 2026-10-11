"""Outcome-blind v2.6 PySnooper eligibility preflight; never calls an LLM.

The only unexposed cases in this project are checked in the pre-frozen v2.6
hash order. Raw container evidence stays on D:; the lock and concise ledger
stay in the Git workspace. A failed case is retained and not replaced by a
case selected after observing an LLM result.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

from build_unexposed_candidate_queue_v1 import OUTPUT as SOURCE_QUEUE
from build_prior_exposure_ledger_v1 import HERE, MANIFEST

V2 = HERE.parent
ENGINE_DIR = V2 / "major_revision_v2_5"
sys.path.insert(0, str(V2 / "major_revision_v2_3"))
sys.path.insert(0, str(ENGINE_DIR))
import preflight_oci_v2 as engine  # noqa: E402

PROFILE = ENGINE_DIR / "results/pysnooper_preflight_v1d/config.json"
PREDECESSOR_LOCK = HERE / "pysnooper_preflight_v1/lock.json"
ROOT = HERE / "pysnooper_preflight_v1b"
QUEUE = ROOT / "queue.json"
CONFIG = ROOT / "config.json"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/pysnooper_preflight_v1b"
RAW = Path(RAW_TEXT)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write("\n")


def plans():
    source = read(SOURCE_QUEUE)
    if source["status"] != "metadata_queue_not_preflighted_not_main_cohort":
        raise ValueError("v2.6 metadata queue is not frozen")
    project = next(row for row in source["projects"] if row["project"] == "PySnooper")
    ordered = [row for row in project["cases_in_frozen_hash_order"]
               if not row["prior_provider_exposure"]]
    manifest_cases = {f"{row['project']}_{row['bug_id']}": row
                      for row in read(MANIFEST)["candidates"]}
    queue = []
    for row in ordered:
        case = dict(manifest_cases[row["case_id"]])
        case["selection_hash"] = row["case_order_sha256"]
        queue.append(case)
    if [f"PySnooper_{row['bug_id']}" for row in queue] != [
            row["case_id"] for row in ordered] or len(queue) != 2:
        raise ValueError("Unexposed PySnooper queue drift")
    config = read(PROFILE)
    if config["python_scope"] != "3.8" or list(config["profiles"]) != ["PySnooper"]:
        raise ValueError("Unexpected PySnooper profile")
    config["status"] = "v2_6_project_eligibility_preflight_only"
    config["environment_deviation"] += (
        " The reused generic engine emits an OCI tag with a v2.5 suffix; "
        "the v2.6 case/lock hashes and separate raw root identify this run.")
    return queue, config


def freeze():
    queue, config = plans()
    if not PREDECESSOR_LOCK.is_file():
        raise ValueError("Missing preserved pre-container v1 lock")
    prior = read(PREDECESSOR_LOCK)
    if (prior["status"] != "frozen_before_v2_6_pysnooper_container_preflight"
            or prior["provider_calls"] != 0
            or prior["raw_root"] == RAW_TEXT):
        raise ValueError("Expected cross-OS path incident is not preserved")
    expected = {
        "status": "v1b_cross_os_path_amendment_before_container",
        "predecessor_lock_sha256": sha(PREDECESSOR_LOCK),
        "predecessor_issue": "Windows Path string for /mnt/d differed from WSL string; zero container/provider calls before amendment",
        "source_queue_sha256": sha(SOURCE_QUEUE),
        "prior_manifest_sha256": sha(MANIFEST),
        "runner_sha256": sha(Path(__file__)),
        "engine_sha256": sha(ENGINE_DIR / "preflight_oci_v2.py"),
        "profile_source_sha256": sha(PROFILE),
        "raw_root": RAW_TEXT,
        "provider_calls": 0,
        "paid_execution_allowed": False,
    }
    if LOCK.exists():
        locked = read(LOCK)
        if (any(locked.get(key) != value for key, value in expected.items())
                or read(QUEUE) != queue or read(CONFIG) != config
                or locked["queue_sha256"] != sha(QUEUE)
                or locked["config_sha256"] != sha(CONFIG)):
            raise ValueError("Preflight lock drift; never rewrite existing evidence")
        return locked
    if ROOT.exists():
        raise FileExistsError("Partial preflight lock directory exists")
    ROOT.mkdir()
    write_new(QUEUE, queue)
    write_new(CONFIG, config)
    lock = {**expected, "queue_sha256": sha(QUEUE),
            "config_sha256": sha(CONFIG),
            "created_at_utc": datetime.now(timezone.utc).isoformat()}
    write_new(LOCK, lock)
    return lock


def audit():
    freeze()
    queue = read(QUEUE)
    rows = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()] if LEDGER.exists() else []
    if len(rows) > len(queue):
        raise ValueError("More preflight rows than frozen cases")
    for index, row in enumerate(rows):
        case = queue[index]
        record = RAW / f"{index:02d}_PySnooper_{case['bug_id']}/preflight_record.json"
        if (row["queue_index"] != index or row["case_id"] != f"PySnooper_{case['bug_id']}"
                or row["selection_hash"] != case["selection_hash"]
                or row["record_sha256"] != sha(record)):
            raise ValueError("Preflight queue/evidence mismatch")
    passed = [row["case_id"] for row in rows if row["status"] == "reproducible"]
    return {"status": "two_cases_qualified" if len(passed) == 2 else
            "project_ineligible" if len(rows) == len(queue) else "preflight_incomplete",
            "attempted": len(rows), "queue_size": len(queue), "qualified_cases": passed,
            "provider_calls": 0, "lock_sha256": sha(LOCK)}


def run_next():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required for container preflight")
    state = audit()
    if state["status"] != "preflight_incomplete":
        return state
    index = state["attempted"]
    case = read(QUEUE)[index]
    out = RAW / f"{index:02d}_PySnooper_{case['bug_id']}"
    out.parent.mkdir(parents=True, exist_ok=True)
    print(json.dumps({"status": "preflight_started", "case_id":
                      f"PySnooper_{case['bug_id']}", "provider_calls": 0}), flush=True)
    result = engine.run_one(case, read(CONFIG), out)
    row = {"queue_index": index, "case_id": f"PySnooper_{case['bug_id']}",
           "selection_hash": case["selection_hash"], "status": result["status"],
           "reason": result.get("reason"), "record_sha256": sha(out / "preflight_record.json"),
           "provider_calls": 0}
    with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--audit", action="store_true")
    modes.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    result = run_next() if args.run_next else audit() if args.audit else {
        "status": freeze()["status"], "lock_sha256": sha(LOCK), "provider_calls": 0}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
