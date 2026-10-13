"""Audit protected public regressions without reselecting tests or model calls."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config_repository_baseline_gate_v2.json"
OUT = HERE / "results" / "repository_baseline_gate_v2"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dispositions(path):
    root = ET.parse(path).getroot()
    records = {}
    for item in root.iter("testcase"):
        key = item.get("classname", "") + "::" + item.get("name", "")
        if key in records:
            raise ValueError("duplicate testcase identity")
        if item.find("error") is not None or item.find("failure") is not None:
            status = "failed"
        elif item.find("skipped") is not None:
            skipped = item.find("skipped")
            status = "expected_failure" if skipped.get("type") == "pytest.xfail" else "skip"
        else:
            status = "passed"
        records[key] = status
    return records


def main():
    settings = json.loads(CONFIG.read_text(encoding="utf-8"))
    build_lock = HERE / settings["candidate_build_lock"]
    frozen = json.loads(build_lock.read_text(encoding="utf-8"))
    inputs = {"config": sha(CONFIG), "runner": sha(Path(__file__)), "candidate_build_lock": sha(build_lock)}
    OUT.mkdir(exist_ok=True)
    lock = OUT / "lock.json"
    if lock.exists():
        if json.loads(lock.read_text(encoding="utf-8"))["inputs"] != inputs:
            raise ValueError("baseline gate inputs changed")
    else:
        with lock.open("x", encoding="utf-8") as handle:
            json.dump({"inputs": inputs, "settings": settings, "frozen_before_repair_model_calls": True}, handle, indent=2)
    cases = []
    missing = []
    for case in frozen["cases"]:
        output = build_lock.parent / case["case_id"]
        summary_file = output / "summary.json"
        if not summary_file.is_file():
            missing.append(case["case_id"])
            continue
        summary = json.loads(summary_file.read_text(encoding="utf-8"))
        selected_file = output / "regression_selection.json"
        selected = json.loads(selected_file.read_text(encoding="utf-8"))
        if selected["nodeids"] != summary["regression_nodeids"] or not selected["frozen_before_test_outcomes"]:
            raise ValueError("regression selection differs from its frozen record")
        buggy_file = output / "candidate_buggy_regression_files" / "tests.xml"
        fixed_file = output / "trusted_fixed_regression_files" / "tests.xml"
        buggy, fixed = dispositions(buggy_file), dispositions(fixed_file)
        active = sum(value == "passed" for value in buggy.values())
        expected = sum(value == "expected_failure" for value in buggy.values())
        processes = [json.loads((output / name).read_text(encoding="utf-8"))
                     for name in ("candidate_buggy_regression.json", "trusted_fixed_regression.json")]
        audit = summary["candidate_audit"]
        passed = (summary["lock_sha256"] == sha(build_lock)
                  and len(buggy) == len(selected["nodeids"]) == settings["regression_items_per_case"]
                  and buggy == fixed and set(buggy.values()) <= {"passed", "expected_failure"}
                  and active >= settings["minimum_active_passes_per_case"]
                  and all(item["return_code"] == 0 for item in processes)
                  and not audit["blocked_paths"] and not audit["missing_forbidden_roots"]
                  and summary["visible_counts"]["failures"] > 0 and summary["visible_counts"]["errors"] == 0)
        cases.append({"case_id": case["case_id"], "project": case["project"],
                      "passed": passed, "active_regression_passes": active,
                      "historical_expected_failures_not_passes": expected,
                      "dispositions": buggy, "images": summary["images"],
                      "summary_sha256": sha(summary_file), "selection_sha256": sha(selected_file),
                      "buggy_xml_sha256": sha(buggy_file), "fixed_xml_sha256": sha(fixed_file)})
    ready = (not missing and len(cases) == settings["case_count"]
             and len({case["project"] for case in cases}) >= settings["minimum_repositories"]
             and all(case["passed"] for case in cases))
    report = {"status": "baseline_gate_passed" if ready else "baseline_gate_incomplete_or_failed",
              "research_results": False, "no_llm_calls": True, "cases": cases, "missing": missing,
              "lock_sha256": sha(lock), "withheld_public_tests_not_novel_hidden_tests": True}
    # A complete evidence report is immutable; progress prints but does not
    # create an authoritative completed report before the six cases exist.
    if ready:
        path = OUT / "audit.json"
        if path.exists():
            if json.loads(path.read_text(encoding="utf-8")) != report:
                raise ValueError("baseline evidence changed after audit")
        else:
            with path.open("x", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2)
    print(json.dumps(report, indent=2))
    if not ready:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
