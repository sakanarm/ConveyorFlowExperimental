"""Resume the second FastAPI candidate after auditing first-case completion.

The v1b freeze premise was too narrow: it rejected its own first completed
case because regression_selection.json now exists. No second-case build or
test was started. This wrapper verifies the first summary and ledger, then
uses the unchanged v1b case-2 build, top-level collection and test rules.
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
import resume_fastapi_candidates_v1c as prior_recovery

HERE = Path(__file__).resolve().parent
ROOT = HERE / "fastapi_candidate_recovery_v1d"
LOCK = ROOT / "lock.json"
FIRST = base.RAW / "00_fastapi_11"


def freeze():
    first = base.read(FIRST / "summary.json")
    rows = [json.loads(line) for line in base.LEDGER.read_text(
        encoding="utf-8").splitlines() if line.strip()]
    if (first["status"] != "candidate_preflight_passed" or
            first["provider_calls"] != 0 or len(rows) < 1 or
            rows[0]["case_id"] != "fastapi_11" or
            rows[0]["summary_sha256"] != base.sha(FIRST / "summary.json") or
            len(first["public_regression_nodeids"]) != 3 or
            not all(pair["common_pass"] for pair in first["regression_pairs"])):
        raise ValueError("First FastAPI candidate completion not auditable")
    stable = {
        "status": "v2_6_fastapi_case2_resume_after_first_candidate_pass",
        "amendment": "Accept verified first-case completion when resuming unchanged second-case gate",
        "first_summary_sha256": base.sha(FIRST / "summary.json"),
        "prior_candidate_lock_sha256": base.sha(base.LOCK),
        "prior_collection_lock_sha256": base.sha(previous.LOCK),
        "prior_reuse_lock_sha256": base.sha(prior_recovery.LOCK),
        "prior_runner_sha256": base.sha(HERE / "resume_fastapi_candidates_v1b.py"),
        "runner_sha256": base.sha(Path(__file__)),
        "provider_calls": 0, "paid_execution_allowed": False,
    }
    if LOCK.exists():
        old = base.read(LOCK)
        if any(old.get(key) != value for key, value in stable.items()):
            raise ValueError("FastAPI case-2 resume lock drift")
        return old
    if ROOT.exists():
        raise FileExistsError("Partial FastAPI case-2 resume root")
    ROOT.mkdir()
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    base.save_new(LOCK, locked)
    return locked


def run_next():
    if sys.platform != "linux" or os.geteuid() != 0:
        raise ValueError("Rootful Linux required")
    freeze()
    rows = [json.loads(line) for line in base.LEDGER.read_text(
        encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 1:
        return {"status": "already_attempted", "attempted": len(rows),
                "provider_calls": 0}
    old_freeze = previous.freeze
    try:
        previous.freeze = lambda: base.read(previous.LOCK)
        return previous.run_next()
    finally:
        previous.freeze = old_freeze


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    result = run_next() if args.run_next else freeze()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
