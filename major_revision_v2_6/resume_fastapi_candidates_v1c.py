"""Reuse verified source-map evidence after a pre-collection filename collision.

v1b stopped before selecting regression nodes because its repeated image
audit tried to create candidate_source_hashes_files a second time. This
wrapper verifies the existing gold-free audit and lets the unchanged v1b
collection and test rules continue. No previous evidence is overwritten.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

import build_fastapi_candidates_v1 as base
import resume_fastapi_candidates_v1b as previous

HERE = Path(__file__).resolve().parent
ROOT = HERE / "fastapi_candidate_recovery_v1c"
LOCK = ROOT / "lock.json"
FIRST = base.RAW / "00_fastapi_11"


def freeze():
    previous.freeze()
    audit_file = FIRST / "candidate_audit_execution.json"
    candidate_map = FIRST / "candidate_source_hashes.json"
    buggy_map = FIRST / "buggy_source_hashes.json"
    if ((FIRST / "regression_selection.json").exists() and not LOCK.exists() or
            (FIRST / "summary.json").exists() and not LOCK.exists() or
            not audit_file.exists() or not candidate_map.exists() or
            not buggy_map.exists()):
        raise ValueError("Pre-collection recovery premise changed")
    candidate_result, buggy_result = base.read(candidate_map), base.read(buggy_map)
    if (candidate_result["return_code"] != 0 or buggy_result["return_code"] != 0 or
            candidate_result["stdout"] != buggy_result["stdout"]):
        raise ValueError("Buggy/candidate source-map mismatch")
    check = base.read(audit_file)
    checks = json.loads(check["stdout"])
    if (check["return_code"] != 0 or checks["forbidden_roots"] or
            checks["forbidden_paths"] or checks["installed_fastapi"]):
        raise ValueError("Gold-free audit mismatch")
    stable = {
        "status": "v2_6_fastapi_reuse_passed_source_map_before_regression_selection",
        "amendment": "Verify and reuse existing candidate/buggy hash maps; do not rerun same-named audit outputs",
        "prior_collection_lock_sha256": base.sha(previous.LOCK),
        "prior_runner_sha256": base.sha(HERE / "resume_fastapi_candidates_v1b.py"),
        "candidate_audit_sha256": base.sha(audit_file),
        "candidate_source_map_sha256": base.sha(candidate_map),
        "buggy_source_map_sha256": base.sha(buggy_map),
        "runner_sha256": base.sha(Path(__file__)),
        "provider_calls": 0, "paid_execution_allowed": False,
    }
    if LOCK.exists():
        old = base.read(LOCK)
        if any(old.get(key) != value for key, value in stable.items()):
            raise ValueError("FastAPI source-map reuse lock drift")
        return old
    if ROOT.exists():
        raise FileExistsError("Partial source-map reuse lock root")
    ROOT.mkdir()
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    base.save_new(LOCK, locked)
    return locked


def existing_audit(candidate, source, output):
    # freeze() rechecks the original image separation and byte-for-byte map.
    freeze()
    return {"source_files": len(json.loads(base.read(
        FIRST / "candidate_source_hashes.json")["stdout"])),
            "forbidden_roots": [], "forbidden_paths": [],
            "installed_fastapi": False,
            "candidate_source_map_sha256": base.sha(FIRST / "candidate_source_hashes.json"),
            "buggy_source_map_sha256": base.sha(FIRST / "buggy_source_hashes.json"),
            "reused_verified_prior_audit": True}


def run_next():
    freeze()
    if previous.audit()["attempted"] != 0:
        return previous.run_next()
    old = previous.previous.candidate_audit
    try:
        previous.previous.candidate_audit = existing_audit
        return previous.run_next()
    finally:
        previous.previous.candidate_audit = old


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--audit", action="store_true")
    modes.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    result = run_next() if args.run_next else previous.audit() if args.audit else freeze()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
