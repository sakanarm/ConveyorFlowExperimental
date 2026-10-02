"""Offline integrity audit for all materialized Real-LLM task bundles."""

from __future__ import annotations

import csv
import json
import tempfile
from collections import Counter
from pathlib import Path

from validator_contract import validate_bundle
from case_bundle_validator import validate


HERE = Path(__file__).resolve().parent


def main() -> int:
    manifest = HERE / "case_manifest.csv"
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    results: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="conveyorflow_case_audit_") as temporary:
        temporary_root = Path(temporary)
        for row in rows:
            bundle = (HERE / row["execution_bundle"]).resolve()
            expected = json.loads((bundle / "expected.json").read_text(encoding="utf-8"))
            oracle_candidate = json.dumps({"answer": expected["answer"]})
            result = validate_bundle(
                bundle_path=bundle,
                validator_command=row["validator_command"],
                candidate_content=oracle_candidate,
                work_path=temporary_root / row["case_id"],
                timeout_seconds=30,
            )
            if not result["passed"]:
                raise AssertionError(f"oracle candidate failed for {row['case_id']}: {result}")
            prompt = (bundle / "prompt.md").read_text(encoding="utf-8")
            answer_leaked = oracle_candidate in prompt
            if answer_leaked:
                raise AssertionError(f"complete oracle answer leaked in prompt for {row['case_id']}")
            negative_passed, _negative_errors = validate({"answer": {}}, expected)
            if negative_passed:
                raise AssertionError(f"empty negative control passed for {row['case_id']}")
            results.append(
                {
                    "case_id": row["case_id"],
                    "workload": row["workload"],
                    "difficulty": int(row["adjudicated_difficulty"]),
                    "validator_type": expected["validator_type"],
                    "oracle_passed": True,
                    "complete_answer_not_leaked": True,
                    "empty_negative_control_rejected": True,
                }
            )
    counts = Counter((row["workload"], row["difficulty"]) for row in results)
    output = {
        "status": "offline_case_bundle_audit_passed",
        "research_results": False,
        "provider_calls": 0,
        "case_count": len(results),
        "workload_difficulty_counts": {
            f"{workload}_D{difficulty}": count
            for (workload, difficulty), count in sorted(counts.items())
        },
        "checks": {
            "all_oracle_candidates_pass": all(row["oracle_passed"] for row in results),
            "complete_oracle_answers_not_in_prompts": all(
                row["complete_answer_not_leaked"] for row in results
            ),
            "all_empty_negative_controls_rejected": all(
                row["empty_negative_control_rejected"] for row in results
            ),
        },
        "cases": results,
    }
    (HERE / "case_bundle_audit.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in output.items() if key != "cases"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
