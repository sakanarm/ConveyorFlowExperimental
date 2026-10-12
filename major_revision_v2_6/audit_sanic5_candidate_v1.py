"""Read-only audit of the Sanic case 5 v2.6 candidate exclusion."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "major_revision_v2_5"))
from audit_black_candidate_v1 import xml_status  # noqa: E402

LOCK = HERE / "sanic5_candidate_v1/lock.json"
RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_6/sanic5_candidate_v1")
PREFLIGHT = Path("/mnt/d/ConveyorFlowRuntime/v2_6/sanic_preflight_v1c/00_sanic_5/preflight_record.json")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def need(value, label):
    if not value:
        raise ValueError(label)


def audit():
    lock, summary, selection = read(LOCK), read(RAW / "summary.json"), read(RAW / "regression_selection.json")
    preflight = read(PREFLIGHT)
    need(lock["status"] == "v2_6_sanic5_gold_free_candidate_frozen_before_provider", "lock status")
    need(lock["runner_sha256"] == sha(HERE / "build_sanic5_candidate_v1.py"), "runner drift")
    need(lock["case"]["preflight_record_sha256"] == sha(PREFLIGHT), "preflight hash")
    need(preflight["status"] == "reproducible" and preflight["provider_calls"] == 0, "preflight contrast")
    need(summary["status"] == "candidate_preflight_failed", "must preserve failure")
    need(summary["provider_calls"] == lock["provider_calls"] == 0, "provider calls")
    need(summary["lock_sha256"] == sha(LOCK), "lock hash")
    audit_info = summary["candidate_audit"]
    need(audit_info["blocked_paths"] == [] and audit_info["missing_forbidden_roots"] == [], "gold leakage")
    need("sanic/log.py" in audit_info["allowed_source_sha256"], "allowed source")
    need(selection["frozen_before_regression_outcomes"] is True, "selection timing")
    collected = read(RAW / "regression_collection.json")
    need(collected["return_code"] == 0 and not collected.get("timeout"), "collection")
    all_nodes = set(line.strip() for line in collected["stdout"].splitlines()
                    if line.startswith(lock["public_regression_file"] + "::") and
                    line.strip() != lock["case"]["visible_test"])
    expected = sorted(all_nodes, key=lambda node: hashlib.sha256((
        lock["regression_selection_domain"] + "|sanic_5|" + node).encode()).hexdigest())[:3]
    need(selection["nodeids"] == summary["public_regression_nodeids"] == expected, "selection reconstruction")
    visible = summary["visible"]
    visible_xml = RAW / "buggy_visible_files/tests.xml"
    counts, states = xml_status(visible_xml)
    need(visible["return_code"] == 1 and not visible["timeout"] and
         visible["counts"] == counts and visible["dispositions"] == states and
         set(states.values()) == {"failed"}, "visible bug outcome")
    need(len(summary["regression_pairs"]) == 2 and
         summary["regression_pairs"][0]["common_pass"] and
         not summary["regression_pairs"][1]["common_pass"], "pair stop rule")
    for index, pair in enumerate(summary["regression_pairs"]):
        need(pair["node"] == expected[index], "pair order")
        for variant in ("buggy", "fixed"):
            report = pair[variant]
            raw = RAW / f"{variant}_regression_{index}.json"
            need(sha(raw) == report["execution_sha256"], "raw hash")
            if index == 0:
                xml = RAW / f"{variant}_regression_{index}_files/tests.xml"
                actual_counts, actual_states = xml_status(xml)
                need(report["return_code"] == 0 and not report["timeout"] and
                     report["counts"] == actual_counts and report["dispositions"] == actual_states and
                     set(actual_states.values()) == {"passed"}, "first pair outcome")
            else:
                cleanup = RAW / f"{variant}_regression_{index}_timeout_cleanup.json"
                need(report["timeout"] and report["return_code"] is None and cleanup.exists(),
                     "second pair timeout/cleanup")
    need(not (RAW / "buggy_regression_2.json").exists(), "stop rule violated")
    return {"status": "independent_candidate_exclusion_audited",
            "case_id": "sanic_5", "provider_calls": 0,
            "reason": "selected public regression node 2 timed out in both buggy and fixed containers",
            "selected_nodes": 3, "attempted_node_pairs": 2,
            "lock_sha256": sha(LOCK), "summary_sha256": sha(RAW / "summary.json")}


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
