"""Independent no-provider audit of amended candidate and public test gates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/candidates_v1b"
OUTPUT = HERE / "results/candidates_v1b_audit.json"
sys.path.insert(0, str(HERE.parent / "major_revision_v2_3"))
from audit_repository_baselines_v2 import dispositions  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audit() -> dict:
    lock = read(ROOT / "lock.json")
    amendment = read(ROOT / "amendment_lock.json")
    manifest = read(HERE / "regression_manifest_v1c.json")
    scope = read(HERE / "source_scope_v1c.json")
    if (lock["status"] != "v2_4_gold_free_candidate_build_frozen_no_provider_calls" or
            amendment["candidate_lock_sha256"] != sha256(ROOT / "lock.json") or
            amendment["baseline_pass_manifest_sha256"] != sha256(
                HERE / "regression_manifest_v1c.json") or
            manifest["preselection_lock_sha256"] != sha256(
                HERE / "results/regression_preselection_v1c/lock.json") or
            lock["provider_calls"] != 0 or amendment["provider_calls"] != 0):
        raise ValueError("Amended candidate lock/manifest provenance mismatch")
    expected = [case["case_id"] for case in lock["cases"]]
    if set(expected) != set(scope) or set(expected) != set(manifest["selections"]):
        raise ValueError("Amended candidate case set mismatch")
    checked = []
    for case in lock["cases"]:
        cid = case["case_id"]
        root = ROOT / cid
        summary_path = root / "summary.json"
        if not summary_path.is_file():
            continue
        row = read(summary_path)
        selection_path = root / "regression_selection.json"
        selected = read(selection_path)
        expected_nodes = manifest["selections"][cid]["nodeids"]
        if (row["case_id"] != cid or row["project"] != case["project"] or
                row["status"] != "candidate_preflight_passed" or
                row["lock_sha256"] != sha256(ROOT / "lock.json") or
                row["provider_calls"] != 0 or
                row["images"]["verifier"] != manifest["selections"][cid][
                    "buggy_verifier_image"] or
                selected["nodeids"] != row["regression_nodeids"] or
                selected["nodeids"] != expected_nodes or
                selected["case_id"] != cid or
                row["active_passes"] < 5 or
                row["candidate_audit"]["blocked_paths"] or
                row["candidate_audit"]["missing_forbidden_roots"] or
                set(row["candidate_audit"]["allowed_source_sha256"]) !=
                set(scope[cid]["allowed_files"])):
            raise ValueError("Candidate scope, image, regression or status mismatch: " + cid)
        reports = row["reports"]
        for label in ("candidate_buggy_visible", "candidate_buggy_regression",
                      "trusted_fixed_regression"):
            report = reports[label]
            xml = root / (label + "_files/tests.xml")
            if not xml.is_file() or report["dispositions"] != dispositions(xml):
                raise ValueError("Candidate JUnit/disposition mismatch: " + cid)
        visible = reports["candidate_buggy_visible"]
        buggy = reports["candidate_buggy_regression"]
        fixed = reports["trusted_fixed_regression"]
        if (visible["return_code"] != 1 or visible["counts"]["failures"] < 1 or
                visible["counts"]["errors"] != 0 or
                buggy["return_code"] != 0 or fixed["return_code"] != 0 or
                buggy["dispositions"] != fixed["dispositions"] or
                len(buggy["dispositions"]) != len(expected_nodes) or
                set(buggy["dispositions"].values()) != {"passed"} or
                row["active_passes"] != len(expected_nodes)):
            raise ValueError("Candidate buggy-fail / baseline-pass / fixed-pass invalid: " + cid)
        checked.append({"case_id": cid, "summary_sha256": sha256(summary_path),
                        "regression_count": len(expected_nodes),
                        "candidate_image": row["images"]["candidate"],
                        "verifier_image": row["images"]["verifier"]})
    ready = len(checked) == len(expected)
    return {"status": "all_candidate_gates_independently_audited" if ready else
            "candidate_gates_incomplete", "expected_cases": len(expected),
            "checked_cases": checked, "candidate_lock_sha256": sha256(ROOT / "lock.json"),
            "amendment_lock_sha256": sha256(ROOT / "amendment_lock.json"),
            "manifest_sha256": sha256(HERE / "regression_manifest_v1c.json"),
            "metadata_note": "v1 builder's frozen_before_test_outcomes means before the amended candidate reruns, not before the separately frozen buggy-baseline preselection; see v1c manifest and amendment.",
            "provider_calls": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.seal:
        if result["status"] != "all_candidate_gates_independently_audited":
            raise ValueError("Cannot seal incomplete candidate gate")
        with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps({"status": result["status"],
                      "expected_cases": result["expected_cases"],
                      "checked_cases": len(result["checked_cases"]),
                      "provider_calls": 0}))


if __name__ == "__main__":
    main()
