"""Independent, read-only audit of the two FastAPI candidate gates.

This checks the frozen selection, raw public JUnit evidence, and gold-free
source maps. Passing is source eligibility only; it is not a Real-LLM result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE / "fastapi_candidates_v1"
RAW = Path("D:/ConveyorFlowRuntime/v2_6/fastapi_candidates_v1")
CAPSULE = HERE / "fastapi_two_candidate_gates_capsule_v1.json"
ORDER = ("fastapi_11", "fastapi_8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def xml_counts(path: Path):
    root = ET.fromstring(path.read_bytes())
    cases = list(root.iter("testcase"))
    return {
        "tests": len(cases),
        "failures": sum(any(child.tag == "failure" for child in case)
                        for case in cases),
        "errors": sum(any(child.tag == "error" for child in case)
                      for case in cases),
        "skipped": sum(any(child.tag == "skipped" for child in case)
                       for case in cases),
    }


def check_test(folder: Path, name: str, reported: dict, should_pass: bool):
    execution = folder / f"{name}.json"
    xml = folder / f"{name}_files/tests.xml"
    raw = read(execution)
    require(sha(execution) == reported["execution_sha256"] and
            sha(xml) == reported["xml_sha256"], f"{name}: evidence hash")
    require(raw["return_code"] == reported["return_code"] and
            not raw.get("timeout") and not reported["timeout"],
            f"{name}: execution state")
    counts = xml_counts(xml)
    require(counts == reported["counts"] and counts["tests"] > 0 and
            counts["errors"] == counts["skipped"] == 0,
            f"{name}: JUnit counts")
    if should_pass:
        require(raw["return_code"] == 0 and counts["failures"] == 0,
                f"{name}: regression did not pass")
    else:
        require(raw["return_code"] != 0 and counts["failures"] > 0,
                f"{name}: visible bug did not fail")
    return counts


def audit():
    lock = read(ROOT / "lock.json")
    require(lock["provider_calls"] == 0 and not lock["paid_execution_allowed"]
            and [case["case_id"] for case in lock["cases"]] == list(ORDER)
            and lock["regressions_per_case"] == 3,
            "Candidate freeze drift")
    rows = [json.loads(line) for line in (ROOT / "ledger.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    require(len(rows) == 2, "Expected exactly two candidate attempts")
    audited = []
    for index, case_id in enumerate(ORDER):
        folder = RAW / f"{index:02d}_{case_id}"
        row = rows[index]
        summary_path = folder / "summary.json"
        summary = read(summary_path)
        require(row == {"queue_index": index, "case_id": case_id,
                        "status": "candidate_preflight_passed",
                        "summary_sha256": sha(summary_path),
                        "provider_calls": 0}, f"{case_id}: ledger drift")
        require(summary["case_id"] == case_id and
                summary["status"] == "candidate_preflight_passed" and
                summary["provider_calls"] == 0 and
                summary["public_tests_not_novel_hidden_tests"] is True,
                f"{case_id}: summary drift")
        source = summary["candidate_audit"]
        audit_run = read(folder / "candidate_audit_v1b.json")
        observed = json.loads(audit_run["stdout"])
        require(audit_run["return_code"] == 0 and observed == {
            "forbidden_roots": [], "forbidden_paths": [],
            "installed_fastapi": False}, f"{case_id}: gold-free audit")
        candidate_map_path = folder / "candidate_source_hashes.json"
        buggy_map_path = folder / "buggy_source_hashes.json"
        candidate_map = json.loads(read(candidate_map_path)["stdout"])
        buggy_map = json.loads(read(buggy_map_path)["stdout"])
        require(candidate_map == buggy_map and
                len(candidate_map) == source["source_files"] > 0 and
                sha(candidate_map_path) == source["candidate_source_map_sha256"]
                and sha(buggy_map_path) == source["buggy_source_map_sha256"],
                f"{case_id}: candidate differs from buggy package")
        for image_type in ("candidate", "verifier"):
            built = read(folder / f"{image_type}_build.json")
            require(built["return_code"] == 0 and
                    summary["images"][image_type].startswith("sha256:"),
                    f"{case_id}: image build")
        selection = read(folder / "regression_selection.json")
        nodes = selection["nodeids"]
        require(selection["frozen_before_regression_outcomes"] is True and
                len(nodes) == len(set(nodes)) == 3 and
                nodes == summary["public_regression_nodeids"] and
                not set(nodes).intersection(lock["cases"][index]["visible_tests"]),
                f"{case_id}: node selection drift")
        collected = read(folder / "regression_collection_toplevel.json")
        require(collected["return_code"] == 0 and not collected.get("timeout"),
                f"{case_id}: collection failed")
        visible = lock["cases"][index]["visible_tests"]
        eligible = {line.strip() for line in collected["stdout"].splitlines()
                    if line.startswith("tests/") and "::" in line and
                    line.strip() not in visible and
                    not any(line.strip().startswith(v + "[") for v in visible)}
        expected = sorted(eligible, key=lambda node: hashlib.sha256((
            lock["selection_domain"] + "|" + case_id + "|" + node
        ).encode()).hexdigest())[:3]
        require(nodes == expected, f"{case_id}: frozen hash selection drift")
        require(len(summary["visible"]) == len(visible) and
                len(summary["regression_pairs"]) == 3,
                f"{case_id}: test count")
        visible_counts = [check_test(folder, f"buggy_visible_{i}", evidence,
                                     False)
                          for i, evidence in enumerate(summary["visible"])]
        for i, (node, pair) in enumerate(zip(nodes, summary["regression_pairs"])):
            require(pair["node"] == node and pair["common_pass"] is True and
                    pair["buggy"]["dispositions"] ==
                    pair["fixed"]["dispositions"] and
                    set(pair["buggy"]["dispositions"].values()) == {"passed"},
                    f"{case_id}: regression pair mismatch")
            for variant in ("buggy", "fixed"):
                check_test(folder, f"{variant}_regression_{i}",
                           pair[variant], True)
        audited.append({"case_id": case_id, "summary_sha256": sha(summary_path),
                        "visible_failing_tests": sum(c["failures"] for c in visible_counts),
                        "common_public_regressions": 3,
                        "candidate_source_files": len(candidate_map)})
    return {"status": "two_candidate_gates_audited_source_eligible_only",
            "project_eligible_for_source_pool": True,
            "real_llm_results": False, "provider_calls": 0,
            "cases": audited, "lock_sha256": sha(ROOT / "lock.json"),
            "ledger_sha256": sha(ROOT / "ledger.jsonl"),
            "raw_root": str(RAW)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.write:
        if CAPSULE.exists():
            require(read(CAPSULE) == result, "Existing capsule drift")
        else:
            with CAPSULE.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(result, stream, indent=2, sort_keys=True)
                stream.write("\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
