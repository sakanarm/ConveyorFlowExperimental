from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "v2" / "real_llm_pilot" / "run_mfec_calibration.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("run_mfec_calibration", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

FIX_SPEC = importlib.util.spec_from_file_location(
    "run_mfec_fixbug_v2", ROOT / "v2" / "real_llm_pilot" / "run_mfec_fixbug_v2.py"
)
assert FIX_SPEC is not None and FIX_SPEC.loader is not None
FIX_MODULE = importlib.util.module_from_spec(FIX_SPEC)
FIX_SPEC.loader.exec_module(FIX_MODULE)


def test_json_validator_accepts_numeric_tolerance() -> None:
    passed, reason = MODULE.validate_json_answer('{"accuracy": 0.9}', {"accuracy": 0.90}, 0.01)
    assert passed
    assert reason == "pass"


def test_repair_validator_normalizes_whitespace() -> None:
    probe = {
        "validator_type": "normalized_exact_repair",
        "expected": "public void X ( ) { return ; }",
    }
    passed, reason = MODULE.validate_probe("public  void X ( ) {\nreturn ; }", probe)
    assert passed
    assert reason == "pass"


def test_wilson_and_contiguous_rank_gate() -> None:
    assert 0.49 < MODULE.wilson_lower(8, 10) < 0.50
    cells = {
        1: {"wilson_lower_95": 0.60},
        2: {"wilson_lower_95": 0.39},
        3: {"wilson_lower_95": 0.90},
    }
    rank, notes = MODULE.assign_rank(cells)
    assert rank == 1
    assert notes and notes[0].startswith("D2")


def test_static_safety_accepts_bounded_function() -> None:
    safe, reason = FIX_MODULE.static_safety_check(
        "def add_one(value):\n    return value + 1", "add_one"
    )
    assert safe
    assert reason == "safe"


def test_static_safety_rejects_import_and_private_attribute() -> None:
    safe_import, _ = FIX_MODULE.static_safety_check(
        "def unsafe(value):\n    import os\n    return value", "unsafe"
    )
    safe_attr, _ = FIX_MODULE.static_safety_check(
        "def unsafe(value):\n    return value.__class__", "unsafe"
    )
    assert not safe_import
    assert not safe_attr


def test_static_safety_allows_dict_fromkeys() -> None:
    safe, reason = FIX_MODULE.static_safety_check(
        "def dedupe(values):\n    return list(dict.fromkeys(values))", "dedupe"
    )
    assert safe
    assert reason == "safe"


def test_executable_validator_runs_hidden_tests() -> None:
    probe = {
        "function_name": "double",
        "tests": [{"args": [4], "expected": 8}, {"args": [-2], "expected": -4}],
    }
    passed, reason, tests = FIX_MODULE.validate_executable(
        "def double(value):\n    return value * 2", probe
    )
    assert passed
    assert reason == "pass"
    assert all(row["passed"] for row in tests)
