"""Independently audit the frozen, exposed-case output-budget pilot.

This verifies persisted evidence only. It makes no provider or container calls.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
LOCK = HERE / "repair_output_budget_pilot_v1/lock.json"
RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_6/repair_output_budget_pilot_v1")
if not RAW.exists():
    RAW = Path("D:/ConveyorFlowRuntime/v2_6/repair_output_budget_pilot_v1")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit() -> dict:
    lock, start, provider, summary = (
        read(path) for path in (
            LOCK, RAW / "request_started.json", RAW / "provider.json",
            RAW / "summary.json"))
    assert lock["case_id"] == summary["case_id"] == "fastapi_8"
    assert all(lock[key] for key in (
        "not_main", "not_first_attempt", "not_allocation_comparison",
        "never_pool_with_main_or_prior_attempts", "no_automatic_retry"))
    assert start["lock_sha256"] == sha(LOCK)
    assert start["prompt_sha256"] == lock["prompt_sha256"] == sha(RAW / "prompt.txt")
    assert start["model_slot"] == lock["model"]["slot"]
    assert lock["runner_sha256"] == sha(HERE / "run_repair_output_budget_pilot_v1.py")
    assert provider["exact_model_version"] == lock["model"]["exact_version"]
    for field in ("provider_request_id", "finish_reason", "input_tokens", "output_tokens"):
        assert summary[field] == provider[field]
    assert summary["response_sha256"] == sha(RAW / "response.txt")
    assert summary["patch_sha256"] == sha(RAW / "patch.diff")
    assert provider["finish_reason"] == "stop"
    assert summary["status"] == "VERIFIED"
    assert len(summary["checks"]) == 4
    observed = {}
    for check in summary["checks"]:
        label = check["label"]
        folder = RAW / label
        execution = read(folder / "execution.json")
        xml = folder / "reports/tests.xml"
        suite = ET.parse(xml).getroot().find("testsuite")
        assert suite is not None
        counts = {name: int(suite.attrib[name]) for name in
                  ("tests", "failures", "errors", "skipped")}
        assert counts["tests"] > 0
        assert counts["failures"] == counts["errors"] == counts["skipped"] == 0
        assert execution["return_code"] == check["return_code"] == 0
        assert check["xml_sha256"] == sha(xml)
        assert check["okay"] is True
        observed[label] = counts
    assert set(observed) == {"visible", "regression", "replay_visible",
                            "replay_regression"}
    return {
        "status": "AUDITED_VERIFIED_EXPOSED_INSTRUMENT_PILOT",
        "case_id": "fastapi_8",
        "not_main_or_allocation_result": True,
        "lock_sha256": sha(LOCK),
        "provider_request_id": provider["provider_request_id"],
        "model_slot": lock["model"]["slot"],
        "input_tokens": provider["input_tokens"],
        "output_tokens": provider["output_tokens"],
        "test_counts": observed,
        "provider_calls": 1,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
