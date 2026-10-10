"""Independent joined audit of original and amended no-provider preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import audit_preflight_v1 as original_audit
import preflight_repair_cases_v1 as original
import preflight_repair_cases_v1b as amended
import select_repair_cases_v1 as selection
import select_repair_cases_v1b as reserve


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "results/preflight_v1b_joined_audit.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit() -> dict:
    original_result = original_audit.audit()
    amendment_result = amended.audit()
    if original_result["started_without_record"] or amendment_result["in_progress"]:
        state = "preflight_in_progress"
    else:
        state = "preflight_completed"
    cohort = load(selection.OUTPUT)
    extension = load(reserve.OUTPUT)
    records = []
    for project in selection.PROJECTS:
        queue = cohort["queues"][project]
        for row in sorted((r for r in original.records() if r["project"] == project),
                          key=lambda r: r["queue_index"]):
            records.append((row, queue[row["queue_index"]],
                            original.ROOT / project / row["case_id"] / "engine_ledger.jsonl",
                            sha256(original.LOCK)))
    for row in amended.records():
        records.append((row, extension["reserve_queue"][row["queue_index"] -
                        extension["original_fastapi_prefix_count"]],
                        amended.ROOT / row["case_id"] / "engine_ledger.jsonl",
                        sha256(amended.LOCK)))
    grouped = {project: [] for project in selection.PROJECTS}
    checked = []
    for row, case, engine_ledger, lock_hash in records:
        if (row["case_id"] != case["case_id"] or
                row["selection_hash"] != case["selection_hash"] or
                row["engine_record_sha256"] != sha256(engine_ledger)):
            raise ValueError("Joined preflight identity/hash mismatch")
        evidence_rows = [json.loads(line) for line in engine_ledger.read_text(
            encoding="utf-8").splitlines() if line.strip()]
        if len(evidence_rows) != 1:
            raise ValueError("Joined preflight engine record count mismatch")
        evidence = evidence_rows[0]
        if (evidence["status"] != row["status"] or
                evidence["selection_hash"] != case["selection_hash"] or
                evidence["no_llm_calls"] is not True or
                evidence["validator_only_image"] is not True):
            raise ValueError("Joined preflight trusted engine mismatch")
        artifact = HERE / evidence["artifact_directory"]
        if (artifact.is_symlink() or not artifact.resolve().is_relative_to(HERE.resolve())
                or load(artifact / "preflight_record.json") != evidence
                or sha256(artifact / "Dockerfile") != evidence["dockerfile_sha256"]
                or sha256(artifact / "build_report.json") != evidence["build_report_sha256"]):
            raise ValueError("Joined preflight artifact tampered")
        if row["status"] == "reproducible":
            if (evidence["buggy_test_failed"] is not True or
                    evidence["fixed_test_passed"] is not True or
                    evidence["test_outcomes"]["buggy"]["failures"] < 1 or
                    evidence["test_outcomes"]["fixed"]["failures"] != 0 or
                    evidence["test_outcomes"]["fixed"]["errors"] != 0):
                raise ValueError("Joined buggy/fixed contrast invalid")
            for side in ("buggy", "fixed"):
                if (sha256(artifact / side / "execution.json") != evidence[
                        side + "_test_report_sha256"] or
                        not (artifact / side / "tests.xml").is_file()):
                    raise ValueError("Joined test report/JUnit absent")
            grouped[row["project"]].append(case["case_id"])
        elif row["status"] != "environment_excluded":
            raise ValueError("Unexpected joined environment status")
        checked.append({"case_id": case["case_id"], "status": row["status"],
                        "engine_record_sha256": row["engine_record_sha256"],
                        "preflight_lock_sha256": lock_hash})
    selected = {project: ids[:selection.TARGET_PER_PROJECT]
                for project, ids in grouped.items()}
    ready = (state == "preflight_completed" and all(
        len(ids) == selection.TARGET_PER_PROJECT for ids in selected.values()))
    return {
        "status": "environment_qualified_not_paid_ready" if ready else state,
        "cohort_v1_sha256": sha256(selection.OUTPUT),
        "cohort_v1b_sha256": sha256(reserve.OUTPUT),
        "preflight_v1_lock_sha256": sha256(original.LOCK),
        "preflight_v1b_lock_sha256": sha256(amended.LOCK),
        "preflight_v1_ledger_sha256": sha256(original.LEDGER),
        "preflight_v1b_ledger_sha256": sha256(amended.LEDGER) if
            amended.LEDGER.is_file() else None,
        "checked_records": checked,
        "qualified_case_ids_by_project": selected,
        "started_without_record": (original_result["started_without_record"] +
                                   amendment_result["in_progress"]),
        "provider_calls": 0,
        "paid_execution_allowed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.seal:
        if result["status"] != "environment_qualified_not_paid_ready":
            raise ValueError("All four repository environment targets required")
        with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps({"status": result["status"],
                      "qualified_case_ids_by_project": result[
                          "qualified_case_ids_by_project"],
                      "checked_records": len(result["checked_records"]),
                      "started_without_record": result["started_without_record"],
                      "provider_calls": 0}))


if __name__ == "__main__":
    main()
