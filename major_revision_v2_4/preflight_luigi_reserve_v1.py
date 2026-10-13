"""Validator-only preflight for the two original Luigi queue reserves."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

import preflight_repair_cases_v1 as original
import select_repair_cases_v1 as selection


HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/preflight_luigi_reserve_v1"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"
AMENDMENT = HERE / "LUIGI_RESERVE_GATE_TH.md"
sys.path.insert(0, str(HERE.parent / "major_revision_v2_3"))
import run_bugsinpy_preflight as engine  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def freeze() -> dict:
    original.audit()
    queue = load(selection.OUTPUT)["queues"]["luigi"]
    if len(queue) != 5 or [case["queue_index"] for case in queue] != list(range(5)):
        raise ValueError("Original frozen Luigi queue changed")
    failures = {}
    for cid in ("luigi_8", "luigi_25"):
        path = HERE / "results/candidates_v1" / cid / "summary.json"
        if load(path)["status"] != "candidate_preflight_failed":
            raise ValueError("Original Luigi candidate gate did not fail: " + cid)
        failures[cid] = sha256(path)
    dependencies = {
        "wrapper": sha256(Path(__file__)),
        "reserve_rule": sha256(AMENDMENT),
        "cohort_v1": sha256(selection.OUTPUT),
        "preflight_v1_lock": sha256(original.LOCK),
        "preflight_v1_ledger": sha256(original.LEDGER),
        "candidate_v1_lock": sha256(HERE / "results/candidates_v1/lock.json"),
        "candidate_gate_failures": failures,
        "trusted_preflight_engine": sha256(
            HERE.parent / "major_revision_v2_3/run_bugsinpy_preflight.py"),
    }
    if LOCK.exists():
        locked = load(LOCK)
        if locked["dependencies_sha256"] != dependencies:
            raise ValueError("Frozen Luigi reserve source/evidence drift")
        return locked
    if ROOT.exists():
        raise FileExistsError("Luigi reserve root exists without lock")
    ROOT.mkdir(parents=True)
    locked = {
        "status": "luigi_original_queue_reserve_no_provider_calls",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dependencies_sha256": dependencies,
        "config_sha256": sha256(original.CONFIG),
        "candidate_ids_in_order": [case["case_id"] for case in queue[3:]],
        "provider_calls": 0,
    }
    save_new(LOCK, locked)
    return locked


def records() -> list[dict]:
    return [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()] if LEDGER.is_file() else []


def audit() -> dict:
    lock = freeze()
    queue = load(selection.OUTPUT)["queues"]["luigi"][3:]
    rows = records()
    if len(rows) > len(queue):
        raise ValueError("Luigi reserve ledger exceeds original queue")
    for index, row in enumerate(rows):
        case = queue[index]
        proof_path = ROOT / case["case_id"] / "engine_ledger.jsonl"
        proof = [json.loads(line) for line in proof_path.read_text(
            encoding="utf-8").splitlines() if line.strip()]
        if (row["case_id"] != case["case_id"] or
                row["queue_index"] != case["queue_index"] or
                row["selection_hash"] != case["selection_hash"] or
                row["engine_record_sha256"] != sha256(proof_path) or
                row["status"] not in ("reproducible", "environment_excluded") or
                len(proof) != 1 or proof[0]["status"] != row["status"] or
                proof[0]["selection_hash"] != case["selection_hash"] or
                proof[0]["config_sha256"] != lock["config_sha256"] or
                proof[0]["no_llm_calls"] is not True):
            raise ValueError("Luigi reserve evidence mismatch")
    in_progress = [case["case_id"] for case in queue if
                   (ROOT / case["case_id"]).exists() and
                   case["case_id"] not in {row["case_id"] for row in rows}]
    return {"status": "luigi_reserve_audited", "records": len(rows),
            "reproducible_case_ids": [row["case_id"] for row in rows
                                      if row["status"] == "reproducible"],
            "in_progress": in_progress, "provider_calls": 0}


def run_next() -> dict:
    if (sys.platform != "linux" or os.geteuid() != 0 or
            os.environ.get("CONVEYORFLOW_CONTAINER_COMMAND") != "podman"):
        raise ValueError("Rootful Linux/Podman only")
    state = audit()
    if state["in_progress"]:
        raise FileExistsError("Luigi reserve case already started; inspect it")
    queue = load(selection.OUTPUT)["queues"]["luigi"][3:]
    index = state["records"]
    if index >= len(queue):
        return {"status": "original_luigi_queue_exhausted", "provider_calls": 0}
    case = queue[index]
    case_root = ROOT / case["case_id"]
    case_root.mkdir(parents=True)
    manifest = case_root / "manifest.json"
    save_new(manifest, {"status": "metadata_only_not_preflighted", "candidates": [case]})
    engine.HERE = HERE
    engine.MANIFEST = manifest
    proof_path = case_root / "engine_ledger.jsonl"
    print(json.dumps({"status": "luigi_reserve_preflight_started",
                      "case_id": case["case_id"], "provider_calls": 0}), flush=True)
    engine.run_next(original.CONFIG, proof_path, f"v24_luigi_reserve_{case['bug_id']}")
    proof = [json.loads(line) for line in proof_path.read_text(
        encoding="utf-8").splitlines() if line.strip()]
    if len(proof) != 1 or proof[0]["selection_hash"] != case["selection_hash"]:
        raise ValueError("Trusted Luigi reserve engine record mismatch")
    row = {"project": "luigi", "queue_index": case["queue_index"],
           "case_id": case["case_id"], "selection_hash": case["selection_hash"],
           "status": proof[0]["status"],
           "engine_record_sha256": sha256(proof_path), "provider_calls": 0}
    with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--freeze", action="store_true")
    options.add_argument("--audit", action="store_true")
    options.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    result = run_next() if args.run_next else audit() if args.audit else {
        "status": freeze()["status"], "lock_sha256": sha256(LOCK),
        "provider_calls": 0}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
