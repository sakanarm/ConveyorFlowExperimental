"""Independently verify v2.4 container preflight evidence, without model calls."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import preflight_repair_cases_v1 as preflight
import select_repair_cases_v1 as selection


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit() -> dict:
    basic = preflight.audit()
    cohort = load(selection.OUTPUT)
    lock = load(preflight.LOCK)
    rows = preflight.records()
    selected = {}
    checked = []
    for project in selection.PROJECTS:
        project_rows = sorted((row for row in rows if row["project"] == project),
                              key=lambda row: row["queue_index"])
        qualified = []
        for row in project_rows:
            case = cohort["queues"][project][row["queue_index"]]
            case_root = preflight.ROOT / project / case["case_id"]
            engine_ledger = case_root / "engine_ledger.jsonl"
            if (row["engine_record_sha256"] != sha256(engine_ledger)
                    or row["case_id"] != case["case_id"]
                    or row["selection_hash"] != case["selection_hash"]):
                raise ValueError("Aggregate/engine identity or hash mismatch")
            engine_rows = [json.loads(line) for line in engine_ledger.read_text(
                encoding="utf-8").splitlines() if line.strip()]
            if len(engine_rows) != 1:
                raise ValueError("Not exactly one trusted preflight record")
            evidence = engine_rows[0]
            if (evidence["status"] != row["status"]
                    or evidence["config_sha256"] != lock["config_sha256"]
                    or evidence["runner_sha256"] != lock["dependencies_sha256"][
                        "trusted_preflight_engine"]
                    or evidence["no_llm_calls"] is not True
                    or evidence["validator_only_image"] is not True):
                raise ValueError("Frozen environment/provenance mismatch")
            artifact = preflight.HERE / evidence["artifact_directory"]
            if (artifact.is_symlink() or not artifact.resolve().is_relative_to(
                    preflight.HERE.resolve())
                    or load(artifact / "preflight_record.json") != evidence
                    or sha256(artifact / "Dockerfile") != evidence["dockerfile_sha256"]
                    or sha256(artifact / "build_report.json") != evidence[
                        "build_report_sha256"]):
                raise ValueError("Trusted preflight artifact changed")
            if row["status"] == "reproducible":
                if (evidence["buggy_test_failed"] is not True
                        or evidence["fixed_test_passed"] is not True
                        or evidence["test_outcomes"]["buggy"]["failures"] < 1
                        or evidence["test_outcomes"]["fixed"]["failures"] != 0
                        or evidence["test_outcomes"]["fixed"]["errors"] != 0):
                    raise ValueError("Buggy-fail/fixed-pass gate unsupported")
                for variant in ("buggy", "fixed"):
                    if sha256(artifact / variant / "execution.json") != evidence[
                            variant + "_test_report_sha256"]:
                        raise ValueError("Test report changed")
                    if not (artifact / variant / "tests.xml").is_file():
                        raise ValueError("JUnit evidence absent")
                qualified.append(case["case_id"])
            elif row["status"] != "environment_excluded":
                raise ValueError("Unrecognized preflight status")
            checked.append({"case_id": case["case_id"], "status": row["status"],
                            "engine_record_sha256": sha256(engine_ledger)})
        selected[project] = qualified[:selection.TARGET_PER_PROJECT]
    in_progress = []
    for project in selection.PROJECTS:
        seen = {row["case_id"] for row in rows if row["project"] == project}
        for case in cohort["queues"][project]:
            if ((preflight.ROOT / project / case["case_id"]).exists()
                    and case["case_id"] not in seen):
                in_progress.append(case["case_id"])
    ready = (not in_progress and all(len(value) == selection.TARGET_PER_PROJECT
                                     for value in selected.values()))
    return {
        "status": ("environment_qualified_not_paid_ready" if ready else
                   "environment_preflight_incomplete_or_excluded"),
        "cohort_sha256": sha256(selection.OUTPUT),
        "preflight_lock_sha256": sha256(preflight.LOCK),
        "ledger_sha256": sha256(preflight.LEDGER) if preflight.LEDGER.is_file() else None,
        "checked_records": checked,
        "qualified_case_ids_by_project": selected,
        "started_without_record": in_progress,
        "provider_calls": 0,
        "candidate_image_and_regression_gates_pending": True,
        "paid_execution_allowed": False,
        "basic_audit_records": basic["records"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.seal:
        if result["status"] != "environment_qualified_not_paid_ready":
            raise ValueError("All four project targets must qualify before sealing")
        output = preflight.HERE / "results/preflight_v1_audit.json"
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps({"status": result["status"],
                      "qualified_case_ids_by_project": result[
                          "qualified_case_ids_by_project"],
                      "started_without_record": result["started_without_record"],
                      "checked_records": len(result["checked_records"]),
                      "provider_calls": 0}))


if __name__ == "__main__":
    main()
