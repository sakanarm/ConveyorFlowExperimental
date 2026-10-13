"""Run amended FastAPI reserve preflight in a separate immutable evidence root."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

import preflight_repair_cases_v1 as prior
import select_repair_cases_v1b as reserve


HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/preflight_v1b"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"
sys.path.insert(0, str(HERE.parent / "major_revision_v2_3"))
import run_bugsinpy_preflight as engine  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def expected_dependencies() -> dict[str, str]:
    return {
        "reserve_cohort": sha256(reserve.OUTPUT),
        "preflight_v1_lock": sha256(prior.LOCK),
        "preflight_v1_ledger": sha256(prior.LEDGER),
        "config_v1": sha256(prior.CONFIG),
        "trusted_engine": sha256(HERE.parent / "major_revision_v2_3/run_bugsinpy_preflight.py"),
        "wrapper": sha256(Path(__file__)),
    }


def freeze() -> dict:
    if not prior.audit()["reproducible_per_project"]["fastapi"] == 2:
        raise ValueError("Amendment applies only to the exhausted 2/3 FastAPI v1 ledger")
    frozen = load(reserve.OUTPUT)
    if frozen != (planned := reserve.plan()) | {
            "created_at_utc": frozen["created_at_utc"]}:
        raise ValueError("Reserve cohort mismatch")
    dependencies = expected_dependencies()
    if LOCK.exists():
        lock = load(LOCK)
        if lock["dependencies_sha256"] != dependencies:
            raise ValueError("Frozen amended preflight drift")
        return lock
    if ROOT.exists():
        raise FileExistsError("Amended preflight root exists without lock")
    ROOT.mkdir(parents=True)
    lock = {
        "status": "fastapi_reserve_preflight_frozen_no_provider_calls",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dependencies_sha256": dependencies,
        "config_sha256": sha256(prior.CONFIG),
        "provider_calls": 0,
    }
    save_new(LOCK, lock)
    return lock


def records() -> list[dict]:
    return [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()] if LEDGER.is_file() else []


def audit() -> dict:
    lock = freeze()
    queue = load(reserve.OUTPUT)["reserve_queue"]
    rows = records()
    if len(rows) > len(queue):
        raise ValueError("Reserve ledger longer than queue")
    for index, row in enumerate(rows):
        case = queue[index]
        if (row["queue_index"] != case["queue_index"] or
                row["case_id"] != case["case_id"] or
                row["selection_hash"] != case["selection_hash"] or
                row["status"] not in ("reproducible", "environment_excluded") or
                row["provider_calls"] != 0):
            raise ValueError("Reserve ledger mismatch")
        proof = ROOT / case["case_id"] / "engine_ledger.jsonl"
        if sha256(proof) != row["engine_record_sha256"]:
            raise ValueError("Reserve engine ledger hash mismatch")
        evidence = [json.loads(line) for line in proof.read_text(
            encoding="utf-8").splitlines() if line.strip()]
        if (len(evidence) != 1 or evidence[0]["status"] != row["status"] or
                evidence[0]["selection_hash"] != case["selection_hash"] or
                evidence[0]["config_sha256"] != lock["config_sha256"] or
                evidence[0]["no_llm_calls"] is not True):
            raise ValueError("Reserve engine evidence mismatch")
    active = [case["case_id"] for case in queue if
              (ROOT / case["case_id"]).exists() and
              case["case_id"] not in {row["case_id"] for row in rows}]
    return {"status": "audited", "records": len(rows),
            "reproducible": sum(row["status"] == "reproducible" for row in rows),
            "in_progress": active, "provider_calls": 0}


def run_next() -> dict:
    if (sys.platform != "linux" or os.geteuid() != 0 or
            os.environ.get("CONVEYORFLOW_CONTAINER_COMMAND") != "podman"):
        raise ValueError("Rootful Linux/Podman only")
    state = audit()
    if state["reproducible"] >= 1:
        return {"status": "fastapi_total_target_met", "provider_calls": 0}
    if state["in_progress"]:
        raise FileExistsError("Reserve case already started; inspect, do not blind rerun")
    queue = load(reserve.OUTPUT)["reserve_queue"]
    index = state["records"]
    if index >= len(queue):
        return {"status": "reserve_exhausted", "provider_calls": 0}
    case = queue[index]
    case_root = ROOT / case["case_id"]
    case_root.mkdir(parents=True)
    manifest = case_root / "manifest.json"
    save_new(manifest, {"status": "metadata_only_not_preflighted", "candidates": [case]})
    engine.HERE = HERE
    engine.MANIFEST = manifest
    local_ledger = case_root / "engine_ledger.jsonl"
    print(json.dumps({"status": "reserve_environment_preflight_started",
                      "case_id": case["case_id"], "provider_calls": 0}), flush=True)
    engine.run_next(prior.CONFIG, local_ledger, f"v24_pfb_{case['case_id']}")
    proof = [json.loads(line) for line in local_ledger.read_text(
        encoding="utf-8").splitlines() if line.strip()]
    if len(proof) != 1 or proof[0]["selection_hash"] != case["selection_hash"]:
        raise ValueError("Trusted engine did not produce matching reserve evidence")
    row = {"project": "fastapi", "queue_index": case["queue_index"],
           "case_id": case["case_id"], "selection_hash": case["selection_hash"],
           "status": proof[0]["status"], "engine_record_sha256": sha256(local_ledger),
           "provider_calls": 0}
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
