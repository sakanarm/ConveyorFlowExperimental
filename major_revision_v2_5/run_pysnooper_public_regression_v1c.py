"""Pre-provider public-regression count amendment for PySnooper bug 3.

The frozen v1b candidate selection contains all four non-visible public tests
in its test file. Its five-pass threshold was impossible; no regression was
run. This amendment keeps those exact four nodes and both image IDs, requires
all four to pass in buggy and fixed, and preserves the failed v1b record.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

import build_pysnooper_candidate_v1 as candidate
import recover_pysnooper_candidate_v1b as recovery

HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/pysnooper_regression_v1c"
LOCK = ROOT / "lock.json"
SUMMARY = ROOT / "summary.json"
PREVIOUS = recovery.ROOT / candidate.CASE_ID


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, payload: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


def stable_lock() -> dict:
    prior = read(PREVIOUS / "summary.json")
    selection = read(PREVIOUS / "regression_selection.json")
    nodes = selection["nodeids"]
    if (prior["status"] != "candidate_preflight_failed" or
            prior["reason"] != "too_few_regressions" or prior["selected"] != 4 or
            len(nodes) != 4 or not selection["frozen_before_test_outcomes"] or
            any((PREVIOUS / name).exists() for name in (
                "buggy_regression.json", "fixed_regression.json"))):
        raise ValueError("Prior gate did not stop solely before outcome on infeasible count")
    return {
        "status": "v2_5_all_four_public_regressions_frozen_before_provider",
        "prior_failed_summary_sha256": sha256(PREVIOUS / "summary.json"),
        "prior_selection_sha256": sha256(PREVIOUS / "regression_selection.json"),
        "prior_recovery_lock_sha256": sha256(recovery.RECOVERY),
        "candidate_image_id": prior["images"]["candidate"],
        "verifier_image_id": prior["images"]["verifier"],
        "validator_source_image_id": read(candidate.LOCK)["case"]["validator_source_image"],
        "visible_test": read(candidate.LOCK)["case"]["visible_test"],
        "non_visible_public_nodes": nodes,
        "minimum_active_passes": 4,
        "rule": "Run all four previously selected non-visible public nodes; require all four active passes with identical buggy/fixed dispositions; do not substitute",
        "runner_sha256": sha256(Path(__file__)),
        "trusted_candidate_runner_sha256": sha256(HERE / "build_pysnooper_candidate_v1.py"),
        "provider_calls": 0, "paid_execution_allowed": False,
    }


def freeze() -> dict:
    stable = stable_lock()
    if LOCK.exists():
        lock = read(LOCK)
        if any(lock.get(key) != value for key, value in stable.items()):
            raise ValueError("Frozen four-test gate drift")
        return lock
    if ROOT.exists():
        raise FileExistsError("Four-test gate root exists without lock")
    ROOT.mkdir(parents=True)
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def run() -> dict:
    if sys.platform != "linux" or os.geteuid() != 0:
        raise ValueError("Rootful Linux/Podman required")
    lock = freeze()
    if SUMMARY.exists():
        return read(SUMMARY)
    if any((ROOT / name).exists() for name in (
            "visible.json", "buggy_regression.json", "fixed_regression.json")):
        raise FileExistsError("Interrupted four-test gate retained; inspect before recovery")
    nodes = lock["non_visible_public_nodes"]
    reports = {
        "visible": candidate.test_run(lock["verifier_image_id"], "/protected",
                                      [lock["visible_test"]], ROOT / "visible.json"),
        "buggy_regression": candidate.test_run(lock["verifier_image_id"], "/protected",
                                               nodes, ROOT / "buggy_regression.json"),
        "fixed_regression": candidate.test_run(lock["validator_source_image_id"], "/fixed",
                                               nodes, ROOT / "fixed_regression.json"),
    }
    visible = reports["visible"]
    buggy, fixed = reports["buggy_regression"], reports["fixed_regression"]
    passed = (
        visible["return_code"] == 1 and visible["counts"] is not None and
        visible["counts"]["failures"] > 0 and visible["counts"]["errors"] == 0 and
        buggy["return_code"] == fixed["return_code"] == 0 and
        buggy["dispositions"] == fixed["dispositions"] and
        len(buggy["dispositions"]) == len(nodes) == 4 and
        set(buggy["dispositions"].values()) == {"passed"} and
        not any(report["timeout"] for report in reports.values())
    )
    summary = {
        "status": "candidate_preflight_passed" if passed else "candidate_preflight_failed",
        "case_id": candidate.CASE_ID,
        "public_regression_count": len(nodes),
        "active_public_regression_passes": sum(
            value == "passed" for value in buggy["dispositions"].values()),
        "reports": reports,
        "lock_sha256": sha256(LOCK), "provider_calls": 0,
        "paid_execution_allowed": False,
        "public_tests_not_novel_hidden_tests": True,
    }
    save_new(SUMMARY, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--freeze", action="store_true")
    action.add_argument("--run", action="store_true")
    args = parser.parse_args()
    result = run() if args.run else freeze()
    print(json.dumps({"status": result["status"], "case_id": candidate.CASE_ID,
                      "lock_sha256": sha256(LOCK), "provider_calls": 0,
                      "paid_execution_allowed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
