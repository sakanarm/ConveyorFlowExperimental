from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "real_llm_pilot" / "run_pilot.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("run_pilot", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_current_final_team_reports_research_blockers() -> None:
    config_path = ROOT / "real_llm_pilot" / "config.mfec_final_team.json"
    cases_path = ROOT / "real_llm_pilot" / "case_manifest.csv"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    cases = MODULE.load_cases(cases_path)

    blockers = MODULE.collect_preflight_blockers(config, cases, cases_path=cases_path)
    codes = {blocker["code"] for blocker in blockers}

    assert "CONFIG_NOT_FROZEN" in codes
    assert "MODEL_VERSION_UNPINNED" in codes
    assert "TOKEN_PRICE_MISSING" in codes
    assert "CASE_NOT_EXECUTABLE" not in codes
    assert "EXECUTION_BUNDLE_MISSING" not in codes
    assert "VALIDATOR_COMMAND_MISSING" not in codes
    assert "ALLOCATION_ENGINE_NOT_FROZEN" not in codes
    assert "ALLOCATION_ENGINE_HASH_MISMATCH" not in codes


def test_complete_preflight_has_no_blockers(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for name in ("prompt.md", "expected.json", "provenance.json", "validator.py"):
        (bundle / name).write_text("{}\n", encoding="utf-8")
    cases_path = tmp_path / "cases.csv"
    cases_path.write_text("placeholder\n", encoding="utf-8")
    engine_path = tmp_path / "allocation_engine.py"
    engine_path.write_text("# frozen test engine\n", encoding="utf-8")
    engine_sha = hashlib.sha256(engine_path.read_bytes()).hexdigest()
    case_lock_path = tmp_path / "case_bundle_lock.json"
    case_lock_path.write_text(
        json.dumps(
            {
                "status": "FROZEN_FOR_EXECUTION",
                "case_count": 1,
                "manifest_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    config = {
        "study_status": "FROZEN_FOR_EXECUTION",
        "models": [
            {
                "slot": "agent_1",
                "exact_version": "provider/model@2026-09-23",
                "input_price_per_million_tokens": 1.0,
                "output_price_per_million_tokens": 2.0,
            }
        ],
        "allocation_engine": {
            "status": "FROZEN_FOR_EXECUTION",
            "module": "allocation_engine.py",
            "sha256": engine_sha,
        },
        "case_bundles": {
            "status": "FROZEN_FOR_EXECUTION",
            "lock_file": "case_bundle_lock.json",
            "sha256": hashlib.sha256(case_lock_path.read_bytes()).hexdigest(),
        },
    }
    cases = [
        {
            "case_id": "RLLM001",
            "execution_bundle": "bundle",
            "validator_command": "python validator.py --candidate {candidate}",
            "executable_ready": "true",
        }
    ]

    assert MODULE.collect_preflight_blockers(config, cases, cases_path=cases_path) == []


def test_frozen_engine_hash_mismatch_is_a_blocker(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for name in ("prompt.md", "expected.json", "provenance.json", "validator.py"):
        (bundle / name).write_text("{}\n", encoding="utf-8")
    cases_path = tmp_path / "cases.csv"
    cases_path.write_text("placeholder\n", encoding="utf-8")
    (tmp_path / "allocation_engine.py").write_text("changed\n", encoding="utf-8")
    case_lock_path = tmp_path / "case_bundle_lock.json"
    case_lock_path.write_text(
        json.dumps(
            {
                "status": "FROZEN_FOR_EXECUTION",
                "case_count": 1,
                "manifest_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    config = {
        "study_status": "FROZEN_FOR_EXECUTION",
        "models": [
            {
                "slot": "agent_1",
                "exact_version": "provider/model@2026-09-23",
                "input_price_per_million_tokens": 1.0,
                "output_price_per_million_tokens": 2.0,
            }
        ],
        "allocation_engine": {
            "status": "FROZEN_FOR_EXECUTION",
            "module": "allocation_engine.py",
            "sha256": "a" * 64,
        },
        "case_bundles": {
            "status": "FROZEN_FOR_EXECUTION",
            "lock_file": "case_bundle_lock.json",
            "sha256": hashlib.sha256(case_lock_path.read_bytes()).hexdigest(),
        },
    }
    cases = [
        {
            "case_id": "RLLM001",
            "execution_bundle": "bundle",
            "validator_command": "python validator.py --candidate {candidate}",
            "executable_ready": "true",
        }
    ]

    blockers = MODULE.collect_preflight_blockers(config, cases, cases_path=cases_path)
    assert [blocker["code"] for blocker in blockers] == ["ALLOCATION_ENGINE_HASH_MISMATCH"]
