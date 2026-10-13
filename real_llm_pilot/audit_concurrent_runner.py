"""Offline concurrency audit for the Real-LLM execution harness.

This uses a sleeping oracle mock, never a provider.  Its output demonstrates
that independent atomic claim winners overlap in wall-clock time and that the
runner emits the required system metrics.  It is infrastructure evidence, not
a ConveyorFlow performance result.
"""

from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import threading
import time
from pathlib import Path

import allocation_engine
import run_pilot


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
            time.sleep(0.08)
            expected_path = HERE / str(case["execution_bundle"]) / "expected.json"
            expected = json.loads(expected_path.read_text(encoding="utf-8"))
            content = json.dumps({"answer": expected["answer"]}, sort_keys=True)
        finally:
            with self._lock:
                self.active -= 1
        return {
            "content": content,
            "provider_request_id": f"offline-mock-{call_number}",
            "exact_model_version": model["exact_version"],
            "input_tokens": 10,
            "output_tokens": 5,
            "latency_seconds": 0.08,
            "finish_reason": "stop",
        }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    with (HERE / "case_manifest.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    selected: list[dict[str, str]] = []
    for difficulty in (1, 2, 3):
        selected.append(
            next(
                row
                for row in manifest
                if row["workload"] == "adult_ml"
                and int(row["adjudicated_difficulty"]) == difficulty
            )
        )

    config = {
        "models": [
            {
                "slot": f"agent_{rank}",
                "model_id": f"offline-model-{rank}",
                "exact_version": f"offline-model-{rank}@frozen",
                "ability_profile": {"ml_build": rank, "fix_bug": rank},
                "input_price_per_million_tokens": float(rank),
                "output_price_per_million_tokens": float(2 * rank),
            }
            for rank in (1, 2, 3)
        ],
        "policies": ["CF_FIT", "S3", "CENTRAL_FIT"],
        "paired_seeds": [3000],
        "generation": {"max_api_retries": 0},
        "validator_timeout_seconds": 30,
        "allocation_engine": {"parameters": {"max_attempts": 1}},
    }
    adapter = SleepingOracleAdapter()
    with tempfile.TemporaryDirectory(prefix="conveyorflow_concurrency_audit_") as temporary:
        result = run_pilot.execute_study(
            config=config,
            cases=selected,
            cases_base=HERE,
            output=Path(temporary) / "output",
            adapter=adapter,
            policy_engine=allocation_engine,
        )

    passed = (
        adapter.calls == 9
        and adapter.maximum_active >= 2
        and all(run["tasks_verified"] == 3 for run in result["runs"])
        and all(run["maximum_concurrent_executions"] >= 2 for run in result["runs"])
        and all(0 < run["resource_utilization"] <= 1 for run in result["runs"])
    )
    audit = {
        "status": "pass" if passed else "fail",
        "research_results": False,
        "provider_calls": 0,
        "mock_calls": adapter.calls,
        "mock_peak_active": adapter.maximum_active,
        "execution_mode": result["execution_mode"],
        "selected_case_ids": [row["case_id"] for row in selected],
        "runner_sha256": _sha256(HERE / "run_pilot.py"),
        "checks": {
            "three_policies_completed": len(result["runs"]) == 3,
            "all_tasks_verified": all(run["tasks_verified"] == 3 for run in result["runs"]),
            "provider_overlap_observed": adapter.maximum_active >= 2,
            "ledger_overlap_observed": all(
                run["maximum_concurrent_executions"] >= 2 for run in result["runs"]
            ),
            "utilization_bounded": all(
                0 < run["resource_utilization"] <= 1 for run in result["runs"]
            ),
        },
        "runs": [
            {
                "policy": run["policy"],
                "tasks_verified": run["tasks_verified"],
                "maximum_concurrent_executions": run["maximum_concurrent_executions"],
                "resource_utilization": run["resource_utilization"],
                "verified_throughput_per_second": run["verified_throughput_per_second"],
                "p95_terminal_flow_time_seconds": run["p95_terminal_flow_time_seconds"],
            }
            for run in result["runs"]
        ],
        "interpretation": (
            "Offline sleeping-oracle infrastructure audit only; values must not be "
            "reported as Real-LLM policy outcomes."
        ),
    }
    (HERE / "concurrent_runner_audit.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
