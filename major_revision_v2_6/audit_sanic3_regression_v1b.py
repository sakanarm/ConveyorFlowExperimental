"""Read-only independent audit of Sanic case 3 pre-LLM candidate gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "major_revision_v2_5"))
from audit_black_candidate_v1 import xml_status  # noqa: E402

ROOT = HERE / "sanic3_regression_v1b"
RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_6/sanic3_regression_v1b")
PRIOR = Path("/mnt/d/ConveyorFlowRuntime/v2_6/sanic3_candidate_v1")
PREFLIGHT = Path("/mnt/d/ConveyorFlowRuntime/v2_6/sanic_preflight_v1c/01_sanic_3/preflight_record.json")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str):
    if not condition:
        raise ValueError(message)


def audit():
    lock, summary, selection = read(ROOT / "lock.json"), read(RAW / "summary.json"), read(RAW / "regression_selection.json")
    preflight = read(PREFLIGHT)
    require(lock["status"] == "v2_6_sanic3_regression_inventory_amended_before_outcomes", "lock status")
    require(lock["runner_sha256"] == digest(HERE / "build_sanic3_regression_v1b.py"), "runner drift")
    require(lock["v1_lock_sha256"] == digest(HERE / "sanic3_candidate_v1/lock.json"), "v1 lock drift")
    require(lock["v1_summary_sha256"] == digest(PRIOR / "summary.json"), "v1 failure evidence drift")
    require(read(PRIOR / "summary.json")["reason"] == "too_few_public_regressions", "v1 amendment reason")
    require(lock["v1_candidate_audit_sha256"] == digest(PRIOR / "candidate_audit_execution.json"), "candidate audit drift")
    candidate = read(PRIOR / "candidate_audit_execution.json")
    audit_payload = json.loads(candidate["stdout"])
    require(audit_payload["blocked_paths"] == [] and audit_payload["missing_forbidden_roots"] == [], "candidate artifact leakage")
    require("sanic/app.py" in audit_payload["allowed_source_sha256"], "allowed source missing")
    require(preflight["status"] == "reproducible" and preflight["provider_calls"] == 0, "preflight contrast")
    require(lock["provider_calls"] == summary["provider_calls"] == 0, "provider calls")
    require(summary["status"] == "candidate_preflight_passed", "candidate status")
    require(summary["lock_sha256"] == digest(ROOT / "lock.json"), "lock hash")
    require(selection["frozen_before_regression_outcomes"] is True, "selection timing")
    nodes = selection["nodeids"]
    require(len(nodes) == len(set(nodes)) == lock["maximum_nodes"] == 5, "node count")
    require(nodes == summary["public_regression_nodeids"], "summary node drift")
    require(all(any(node.startswith(path + "::") for path in lock["public_test_files"]) for node in nodes), "out-of-scope node")
    collection = read(RAW / "regression_collection.json")
    require(collection["return_code"] == 0 and not collection.get("timeout"), "collection outcome")
    all_nodes = set(line.strip() for line in collection["stdout"].splitlines()
                    if any(line.startswith(path + "::") for path in lock["public_test_files"]))
    expected = sorted(all_nodes, key=lambda node: hashlib.sha256((
        lock["selection_domain"] + "|sanic_3|" + node).encode()).hexdigest())[:5]
    require(nodes == expected, "hash-selection not reconstructed")
    expected_outcomes = {"buggy_visible": (1, 1, "failed"),
                         "buggy_regression": (0, 5, "passed"),
                         "fixed_regression": (0, 5, "passed")}
    for label, (rc, count, state) in expected_outcomes.items():
        report = summary["reports"][label]
        raw = RAW / (label + ".json")
        xml = RAW / (label + "_files/tests.xml")
        require(digest(raw) == report["execution_sha256"] and
                digest(xml) == report["xml_sha256"], label + " evidence hash")
        counts, states = xml_status(xml)
        require(counts == report["counts"] and states == report["dispositions"], label + " JUnit mismatch")
        require(report["return_code"] == rc and not report["timeout"] and
                len(states) == count and set(states.values()) == {state}, label + " test outcome")
    require(summary["reports"]["buggy_regression"]["dispositions"] ==
            summary["reports"]["fixed_regression"]["dispositions"] and
            summary["active_public_regression_passes"] == 5, "common regression passes")
    return {"status": "independent_candidate_audit_passed",
            "case_id": "sanic_3", "provider_calls": 0,
            "public_regression_nodes": 5,
            "preflight_record_sha256": digest(PREFLIGHT),
            "lock_sha256": digest(ROOT / "lock.json"),
            "summary_sha256": digest(RAW / "summary.json"),
            "candidate_image_id": lock["candidate_image_id"],
            "verifier_image_id": lock["verifier_image_id"]}


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
