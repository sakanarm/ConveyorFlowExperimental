"""Independent read-only audit of new-repository feasibility gates.

The gate auditor never calls a model or runs generated patches. It verifies
locked preflight identity, image separation, original failures, amended public
test selection, and reported terminal outcomes from retained OCI evidence.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / "results/new_repo_gates_audit_v1.json"
sys.path.insert(0, str(HERE.parent / "major_revision_v2_3"))
from audit_repository_baselines_v2 import dispositions  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit() -> dict:
    results = HERE / "results"
    sanic_pf = results / "sanic_preflight_v1"
    sanic_ledger = [json.loads(line) for line in (
        sanic_pf / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(sanic_ledger) != 1 or sanic_ledger[0]["status"] != "reproducible":
        raise ValueError("Sanic preflight identity changed")
    sanic_record = results / "v25_sanic_5/000_sanic_5/preflight_record.json"
    if (read(sanic_record)["test_outcomes"]["buggy"]["failures"] != 1 or
            read(sanic_record)["test_outcomes"]["fixed"]["return_code"] != 0):
        raise ValueError("Sanic buggy/fixed contrast absent")
    sanic_candidate = results / "sanic_candidate_v1/sanic_5/summary.json"
    sanic = read(sanic_candidate)
    if (sanic["status"] != "candidate_preflight_failed" or
            not sanic["reports"]["buggy_regression"]["timeout"] or
            not sanic["reports"]["fixed_regression"]["timeout"]):
        raise ValueError("Sanic regression exclusion changed")

    cohort = read(results / "pysnooper_preflight_v1/queue.json")["candidates"]
    pf_root = results / "pysnooper_preflight_v1d"
    pf_rows = [json.loads(line) for line in (
        pf_root / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if (len(pf_rows) != 1 or pf_rows[0]["bug_id"] != cohort[0]["bug_id"] or
            pf_rows[0]["selection_hash"] != cohort[0]["selection_hash"] or
            pf_rows[0]["status"] != "reproducible"):
        raise ValueError("PySnooper frozen queue or preflight changed")
    pf_record_file = pf_root / "00_pysnooper_3/preflight_record.json"
    pf_record = read(pf_record_file)
    if (sha256(pf_record_file) != pf_rows[0]["record_sha256"] or
            pf_record["test_outcomes"]["buggy"] != {
                "return_code": 1, "tests": 1, "failures": 1, "errors": 0, "skipped": 0} or
            pf_record["test_outcomes"]["fixed"] != {
                "return_code": 0, "tests": 1, "failures": 0, "errors": 0, "skipped": 0}):
        raise ValueError("PySnooper buggy/fixed preflight evidence changed")
    candidate_root = results / "pysnooper_candidate_v1b/PySnooper_3"
    candidate = read(candidate_root / "summary.json")
    selection = read(candidate_root / "regression_selection.json")
    gate_root = results / "pysnooper_regression_v1c"
    gate_lock = read(gate_root / "lock.json")
    final = read(gate_root / "summary.json")
    if (candidate["status"] != "candidate_preflight_failed" or
            candidate["reason"] != "too_few_regressions" or
            candidate["selected"] != 4 or
            gate_lock["prior_failed_summary_sha256"] != sha256(candidate_root / "summary.json") or
            gate_lock["prior_selection_sha256"] != sha256(candidate_root / "regression_selection.json") or
            gate_lock["non_visible_public_nodes"] != selection["nodeids"] or
            final["lock_sha256"] != sha256(gate_root / "lock.json")):
        raise ValueError("Public regression amendment provenance changed")
    audit_image = candidate["candidate_audit"]
    if (audit_image["blocked_paths"] or audit_image["missing_forbidden_roots"] or
            set(audit_image["allowed_source_sha256"]) != {"pysnooper/pysnooper.py"} or
            gate_lock["candidate_image_id"] == gate_lock["validator_source_image_id"]):
        raise ValueError("Gold-free candidate boundary absent")
    selected = selection["nodeids"]
    buggy_xml = gate_root / "buggy_regression_files/tests.xml"
    fixed_xml = gate_root / "fixed_regression_files/tests.xml"
    bug, fix = dispositions(buggy_xml), dispositions(fixed_xml)
    if (final["status"] != "candidate_preflight_passed" or len(selected) != 4 or
            len(bug) != 4 or bug != fix or set(bug.values()) != {"passed"} or
            final["active_public_regression_passes"] != 4 or
            final["reports"]["visible"]["counts"]["failures"] < 1 or
            any(report["timeout"] for report in final["reports"].values())):
        raise ValueError("Four-test public regression gate failed independent audit")
    for label, path in (("buggy_regression", buggy_xml), ("fixed_regression", fixed_xml)):
        if final["reports"][label]["xml_sha256"] != sha256(path):
            raise ValueError("Test XML drift: " + label)
    return {
        "status": "one_new_repo_candidate_gate_audited",
        "new_source_repository_ready_for_later_paid_extension": "PySnooper",
        "ready_case_id": "PySnooper_3",
        "sanic_status": "preflight_passed_candidate_gate_failed_network_isolated_regression_timeout",
        "pysnooper_visible_buggy_failures": 1,
        "pysnooper_fixed_visible_passes": 1,
        "pysnooper_public_regression_common_passes": 4,
        "independent_new_repo_paid_results": 0,
        "provider_calls": 0,
        "statistical_generalization_gap_closed": False,
        "cost_completeness_gap_closed": False,
        "sanic_preflight_record_sha256": sha256(sanic_record),
        "sanic_candidate_summary_sha256": sha256(sanic_candidate),
        "pysnooper_preflight_record_sha256": sha256(pf_record_file),
        "pysnooper_regression_summary_sha256": sha256(gate_root / "summary.json"),
    }


def main() -> None:
    result = audit()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        if read(OUT) != result:
            raise ValueError("Existing audit output changed; preserve it")
    else:
        with OUT.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
