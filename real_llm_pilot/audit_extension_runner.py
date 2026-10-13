"""Offline infrastructure audit for the frozen Real-LLM extension.

This never contacts a provider and its measurements are not research results.
"""

from __future__ import annotations

import csv
import json
import tempfile
import threading
import time
from pathlib import Path

import allocation_engine_extension
import run_extension


HERE = Path(__file__).resolve().parent


class SleepingOracleAdapter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.active = 0
        self.maximum_active = 0
        self.calls = 0

    def invoke(self, *, model: dict, case: dict, generation: dict) -> dict:
        with self._lock:
            self.active += 1
            self.maximum_active = max(self.maximum_active, self.active)
            self.calls += 1
            call_number = self.calls
        try:
            time.sleep(0.03)
            expected_path = HERE / str(case["execution_bundle"]) / "expected.json"
            expected = json.loads(expected_path.read_text(encoding="utf-8"))
            content = json.dumps({"answer": expected["answer"]}, sort_keys=True)
        finally:
            with self._lock:
                self.active -= 1
        return {
            "content": content,
            "provider_request_id": f"offline-extension-mock-{call_number}",
            "exact_model_version": model["exact_version"],
            "input_tokens": 10,
            "output_tokens": 5,
            "latency_seconds": 0.03,
            "finish_reason": "stop",
        }


def _config(policy: str, *, homogeneous: bool) -> dict:
    versions = ["same@frozen"] * 3 if homogeneous else [f"model-{rank}@frozen" for rank in (1, 2, 3)]
    return {
        "condition_id": f"audit-{policy}-{'hom' if homogeneous else 'het'}",
        "models": [
            {
                "slot": f"agent_{rank}",
                "model_id": versions[rank - 1],
                "exact_version": versions[rank - 1],
                "ability_profile": {"ml_build": rank, "fix_bug": rank},
                "input_price_per_million_tokens": float(rank),
                "output_price_per_million_tokens": float(rank * 2),
            }
            for rank in (1, 2, 3)
        ],
        "policies": [policy],
        "paired_seeds": [3000],
        "generation": {"max_api_retries": 0},
        "validator_timeout_seconds": 30,
        "allocation_engine": {"parameters": {"max_attempts": 1}},
    }


def main() -> int:
    with (HERE / "case_manifest.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    selected = [
        next(
            row
            for row in manifest
            if row["workload"] == "adult_ml" and int(row["adjudicated_difficulty"]) == difficulty
        )
        for difficulty in (1, 2, 3)
    ]
    conditions = [
        ("CF_FIT", False),
        ("CF_FIT_NO_STANDDOWN", False),
        ("CF_FIT", True),
    ]
    rows = []
    all_pass = True
    with tempfile.TemporaryDirectory(prefix="conveyorflow_extension_audit_") as temporary:
        for index, (policy, homogeneous) in enumerate(conditions):
            adapter = SleepingOracleAdapter()
            result = run_extension.execute_study(
                config=_config(policy, homogeneous=homogeneous),
                cases=selected,
                cases_base=HERE,
                output=Path(temporary) / f"condition_{index}",
                adapter=adapter,
                policy_engine=allocation_engine_extension,
            )
            run = result["runs"][0]
            condition_pass = (
                run["tasks_verified"] == 3
                and adapter.maximum_active >= 2
                and run["maximum_concurrent_executions"] >= 2
            )
            all_pass = all_pass and condition_pass
            rows.append(
                {
                    "policy": policy,
                    "homogeneous": homogeneous,
                    "pass": condition_pass,
                    "tasks_verified": run["tasks_verified"],
                    "mock_calls": adapter.calls,
                    "mock_peak_active": adapter.maximum_active,
                    "ledger_peak_active": run["maximum_concurrent_executions"],
                    "stand_down_events": run["event_counts"].get("stand_down", 0),
                }
            )
    if rows[1]["stand_down_events"] != 0:
        all_pass = False
    audit = {
        "status": "pass" if all_pass else "fail",
        "research_results": False,
        "provider_calls": 0,
        "purpose": "offline extension execution-path audit only",
        "conditions": rows,
    }
    (HERE / "extension_runner_audit.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, indent=2))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

