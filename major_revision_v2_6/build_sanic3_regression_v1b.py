"""Pre-LLM Sanic case 3 public-regression inventory amendment.

V1 found that the metadata's test_url_for.py has only the visible test. This
amendment broadens only the public regression inventory to three semantically
related test files, chosen before their outcomes. It reuses the same audited
gold-free candidate/verifier images and does not call an LLM.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_sanic3_candidate_v1 as prior  # noqa: E402

CASE_ID = prior.CASE_ID
LOCK_ROOT = HERE / "sanic3_regression_v1b"
LOCK = LOCK_ROOT / "lock.json"
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/sanic3_regression_v1b"
RAW = Path(RAW_TEXT if os.name != "nt" else "D:/ConveyorFlowRuntime/v2_6/sanic3_regression_v1b")
TEST_FILES = [
    "tests/test_named_routes.py",
    "tests/test_routes.py",
    "tests/test_url_building.py",
]
MAX_NODES = 5
MIN_ACTIVE_PASSES = 3
DOMAIN = "cf-v26-sanic3-public-route-regressions-20261011-v1b"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def freeze():
    v1 = read(prior.RAW / "summary.json")
    if (v1 != {"case_id": CASE_ID, "provider_calls": 0,
               "reason": "too_few_public_regressions", "selected_nodes": 0,
               "status": "candidate_preflight_failed"} or
            read(prior.RAW / "regression_selection.json")["nodeids"] != []):
        raise ValueError("Expected preserved v1 no-regression outcome")
    v1_images = {
        target: prior.inspect(f"conveyorflow-v26-sanic3-{target}:v1")
        for target in ("candidate", "verifier")
    }
    stable = {
        "status": "v2_6_sanic3_regression_inventory_amended_before_outcomes",
        "case_id": CASE_ID,
        "reason_for_amendment": "V1 metadata test file has only the visible test; zero non-visible regression nodes",
        "public_test_files": TEST_FILES,
        "selection_rule": "Hash-sort collected nodes in three declared public route/URL files and take first five",
        "selection_domain": DOMAIN,
        "maximum_nodes": MAX_NODES,
        "minimum_active_passes": MIN_ACTIVE_PASSES,
        "v1_lock_sha256": sha(prior.LOCK),
        "v1_summary_sha256": sha(prior.RAW / "summary.json"),
        "v1_candidate_audit_sha256": sha(prior.RAW / "candidate_audit_execution.json"),
        "candidate_image_id": v1_images["candidate"],
        "verifier_image_id": v1_images["verifier"],
        "runner_sha256": sha(Path(__file__)),
        "provider_calls": 0,
        "paid_execution_allowed": False,
        "raw_root": RAW_TEXT,
    }
    if LOCK.exists():
        old = read(LOCK)
        if any(old.get(key) != val for key, val in stable.items()):
            raise ValueError("V1b lock drift")
        return old
    if LOCK_ROOT.exists():
        raise FileExistsError("Partial V1b lock root")
    LOCK_ROOT.mkdir()
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def run():
    if sys.platform != "linux" or os.geteuid() != 0 or prior.executable() != "podman":
        raise ValueError("Rootful Linux/Podman required")
    locked = freeze()
    if RAW.exists():
        if (RAW / "summary.json").exists():
            return read(RAW / "summary.json")
        raise FileExistsError("Partial V1b attempt retained; audit before retry")
    RAW.mkdir(parents=True)
    command = (
        "cp -a /protected /tmp/work && cd /tmp/work && PYTHONPATH=/tmp/work "
        "python -m pytest --collect-only -q " + " ".join(TEST_FILES)
    )
    collected, _ = prior.container(locked["verifier_image_id"], command,
                                   RAW / "regression_collection.json",
                                   timeout=prior.SETTINGS["test_timeout_seconds"])
    if collected["return_code"] != 0 or collected.get("timeout"):
        summary = {"status": "candidate_preflight_failed", "reason": "public_collection_failed",
                   "case_id": CASE_ID, "collection_return_code": collected["return_code"],
                   "collection_timeout": bool(collected.get("timeout")), "provider_calls": 0}
        save_new(RAW / "summary.json", summary)
        return summary
    nodes = sorted(set(
        line.strip() for line in collected["stdout"].splitlines()
        if any(line.startswith(path + "::") for path in TEST_FILES)
    ), key=lambda node: hashlib.sha256((DOMAIN + "|" + CASE_ID + "|" + node).encode()).hexdigest())[:MAX_NODES]
    save_new(RAW / "regression_selection.json", {
        "nodeids": nodes, "selection_rule": locked["selection_rule"],
        "frozen_before_regression_outcomes": True,
    })
    if len(nodes) < MIN_ACTIVE_PASSES:
        summary = {"status": "candidate_preflight_failed", "reason": "too_few_collected_nodes",
                   "case_id": CASE_ID, "selected_nodes": len(nodes), "provider_calls": 0}
        save_new(RAW / "summary.json", summary)
        return summary
    case = prior.case_spec()
    reports = {
        "buggy_visible": prior.run_test(locked["verifier_image_id"], "/protected",
                                        [case["visible_test"]], RAW / "buggy_visible.json"),
        "buggy_regression": prior.run_test(locked["verifier_image_id"], "/protected",
                                           nodes, RAW / "buggy_regression.json"),
        "fixed_regression": prior.run_test(case["validator_source_image"], "/fixed",
                                           nodes, RAW / "fixed_regression.json"),
    }
    visible, buggy, fixed = (reports[key] for key in ("buggy_visible", "buggy_regression", "fixed_regression"))
    active = sum(value == "passed" for value in buggy["dispositions"].values())
    passed = (
        visible["return_code"] == 1 and visible["counts"] is not None and
        visible["counts"]["failures"] > 0 and visible["counts"]["errors"] == 0 and
        buggy["return_code"] == fixed["return_code"] == 0 and
        buggy["dispositions"] == fixed["dispositions"] and
        len(buggy["dispositions"]) == len(nodes) and
        set(buggy["dispositions"].values()) <= {"passed", "expected_failure"} and
        active >= MIN_ACTIVE_PASSES and
        not any(row["timeout"] for row in reports.values())
    )
    summary = {
        "status": "candidate_preflight_passed" if passed else "candidate_preflight_failed",
        "case_id": CASE_ID, "public_regression_nodeids": nodes,
        "active_public_regression_passes": active, "reports": reports,
        "lock_sha256": sha(LOCK), "provider_calls": 0,
        "paid_execution_allowed": False,
        "public_tests_not_novel_hidden_tests": True,
    }
    save_new(RAW / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--run", action="store_true")
    args = parser.parse_args()
    result = run() if args.run else freeze()
    print(json.dumps({"status": result["status"], "case_id": CASE_ID,
                      "lock_sha256": sha(LOCK), "provider_calls": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
