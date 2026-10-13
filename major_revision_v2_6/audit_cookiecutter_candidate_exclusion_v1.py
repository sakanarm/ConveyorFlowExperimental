"""Read-only audit of the first Cookiecutter candidate-gate exclusion.

Public contrast is not sufficient: the pre-frozen same-file regression rule
required three non-visible nodes, but only one was collected. No regression
outcome or LLM result is inferred from this source-eligibility failure.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import build_cookiecutter_candidates_v1 as candidate

HERE = Path(__file__).resolve().parent
FIRST = candidate.RAW / "00_cookiecutter_3"
AMENDMENT = HERE / "cookiecutter_candidate_recovery_v1b" / "lock.json"
CAPSULE = HERE / "cookiecutter_candidate_exclusion_capsule_v1.json"


def require(value, message):
    if not value:
        raise ValueError(message)


def audit():
    lock, amendment = candidate.read(candidate.LOCK), candidate.read(AMENDMENT)
    summary = candidate.read(FIRST / "summary.json")
    selection = candidate.read(FIRST / "regression_selection.json")
    rows = [json.loads(line) for line in candidate.LEDGER.read_text(
        encoding="utf-8").splitlines() if line.strip()]
    require(lock["runner_sha256"] == candidate.sha(HERE / "build_cookiecutter_candidates_v1.py")
            and amendment["runner_sha256"] ==
            candidate.sha(HERE / "resume_cookiecutter_candidate_v1b.py")
            and amendment["original_lock_sha256"] == candidate.sha(candidate.LOCK),
            "Frozen runner/lock drift")
    require(len(rows) == 1 and rows[0]["case_id"] == "cookiecutter_3" and
            rows[0]["summary_sha256"] == candidate.sha(FIRST / "summary.json") and
            rows[0]["provider_calls"] == 0, "Ledger/evidence mismatch")
    original_candidate = candidate.read(FIRST / "candidate_build.json")
    original_verifier = candidate.read(FIRST / "verifier_build.json")
    require(original_candidate["return_code"] == 0 and
            original_verifier["return_code"] == 125 and
            "layer not known" in original_verifier["stderr"] and
            amendment["first_candidate_build_sha256"] ==
            candidate.sha(FIRST / "candidate_build.json") and
            amendment["first_verifier_build_sha256"] ==
            candidate.sha(FIRST / "verifier_build.json"),
            "Initial cache failure/amendment mismatch")
    for variant in ("candidate", "verifier"):
        rebuilt = candidate.read(FIRST / f"{variant}_build_nocache.json")
        require(rebuilt["return_code"] == 0 and not rebuilt.get("timeout"),
                f"{variant} no-cache build failed")
    candidate_map = candidate.read(FIRST / "candidate_source_hashes.json")
    buggy_map = candidate.read(FIRST / "buggy_source_hashes.json")
    require(candidate_map["stdout"] == buggy_map["stdout"],
            "Candidate/buggy source maps differ")
    image_audit = candidate.read(FIRST / "candidate_audit_execution.json")
    require(image_audit["return_code"] == 0 and
            '"forbidden_roots": []' in image_audit["stdout"] and
            '"forbidden_paths": []' in image_audit["stdout"],
            "Forbidden candidate material found")
    require(lock["regressions_per_case"] == 3 and
            selection["frozen_before_regression_outcomes"] is True and
            len(selection["nodeids"]) == 1 and
            summary == {"case_id": "cookiecutter_3", "provider_calls": 0,
                        "reason": "too_few_public_nodes", "selected_nodes": 1,
                        "status": "candidate_preflight_failed"},
            "Candidate exclusion decision drift")
    require(not list(FIRST.glob("*regression_0.json")) and
            not (FIRST / "buggy_visible.json").exists(),
            "Unexpected test outcome after node-count exclusion")
    return {"status": "cookiecutter_excluded_under_frozen_candidate_gate",
            "case_id": "cookiecutter_3", "project_eligible_for_main": False,
            "reason": "one_non_visible_same_file_node_below_three_required",
            "provider_calls": 0,
            "candidate_lock_sha256": candidate.sha(candidate.LOCK),
            "amendment_lock_sha256": candidate.sha(AMENDMENT),
            "summary_sha256": candidate.sha(FIRST / "summary.json"),
            "ledger_sha256": candidate.sha(candidate.LEDGER)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.write:
        if CAPSULE.exists():
            require(candidate.read(CAPSULE) == result, "Existing capsule drift")
        else:
            with CAPSULE.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(result, stream, indent=2, sort_keys=True)
                stream.write("\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
