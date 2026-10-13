from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "real_llm_pilot"
sys.path.insert(0, str(PILOT))

from case_bundle_validator import validate  # noqa: E402


def test_all_60_bundles_are_materialized_and_structured() -> None:
    with (PILOT / "case_manifest.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 60
    assert all(row["executable_ready"].lower() == "true" for row in rows)
    assert all(
        row["validator_command"] == "python validator.py --candidate {candidate}"
        for row in rows
    )
    for row in rows:
        bundle = PILOT / row["execution_bundle"]
        assert bundle.is_dir()
        assert {"prompt.md", "expected.json", "provenance.json", "validator.py"} <= {
            path.name for path in bundle.iterdir()
        }


def test_each_oracle_answer_passes_validator_logic() -> None:
    with (PILOT / "case_manifest.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        expected = json.loads(
            (PILOT / row["execution_bundle"] / "expected.json").read_text(encoding="utf-8")
        )
        passed, errors = validate({"answer": expected["answer"]}, expected)
        assert passed, (row["case_id"], errors)


def test_bugs2fix_cases_are_explicitly_bounded_surrogates() -> None:
    with (PILOT / "case_manifest.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        rows = [row for row in csv.DictReader(handle) if row["workload"] == "bugs2fix"]
    assert len(rows) == 20
    for row in rows:
        bundle = PILOT / row["execution_bundle"]
        provenance = json.loads((bundle / "provenance.json").read_text(encoding="utf-8"))
        prompt = (bundle / "prompt.md").read_text(encoding="utf-8")
        assert provenance["construction"] == "executable_behavioral_surrogate"
        assert provenance["claim_boundary"] == "not_repository_level_program_repair"
        assert "not a repository-level Java" in prompt
