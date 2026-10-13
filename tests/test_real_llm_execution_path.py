from __future__ import annotations

import importlib.util
import json
import sys
import threading
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "real_llm_pilot"
sys.path.insert(0, str(PILOT))
SPEC = importlib.util.spec_from_file_location("real_llm_runner_execution_test", PILOT / "run_pilot.py")
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class MockAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def invoke(self, *, model: dict, case: dict, generation: dict) -> dict:
        self.calls.append((model["slot"], case["case_id"]))
        return {
            "content": "expected",
            "provider_request_id": f"request-{len(self.calls)}",
            "exact_model_version": model["exact_version"],
            "input_tokens": 10,
            "output_tokens": 2,
            "latency_seconds": 0.1,
            "finish_reason": "stop",
        }


VALIDATOR = """\
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--candidate', required=True)
args = parser.parse_args()
content = Path(args.candidate).read_text(encoding='utf-8')
print(json.dumps({'passed': content == 'expected'}))
"""


def test_execution_calls_only_atomic_claim_winner(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "validator.py").write_text(VALIDATOR, encoding="utf-8")
    (bundle / "prompt.md").write_text("Return the expected value.", encoding="utf-8")
    cases = [
        {
            "case_id": "RLLM001",
            "workload": "adult_ml",
            "adjudicated_difficulty": "1",
            "execution_bundle": "bundle",
            "validator_command": "python validator.py --candidate {candidate}",
            "executable_ready": "true",
        }
    ]
    config = {
        "models": [
            {
                "slot": "agent_1",
                "model_id": "low",
                "exact_version": "low@1",
                "ability_profile": {"ml_build": 1, "fix_bug": 1},
                "input_price_per_million_tokens": 1.0,
                "output_price_per_million_tokens": 2.0,
            },
            {
                "slot": "agent_2",
                "model_id": "high",
                "exact_version": "high@1",
                "ability_profile": {"ml_build": 3, "fix_bug": 3},
                "input_price_per_million_tokens": 3.0,
                "output_price_per_million_tokens": 6.0,
            },
        ],
        "policies": ["CF_FIT", "S3", "CENTRAL_FIT"],
        "paired_seeds": [3000],
        "generation": {"max_api_retries": 0},
        "validator_timeout_seconds": 10,
        "allocation_engine": {
            "parameters": {
                "k_scan": 8,
                "w1": 2,
                "w2": 4,
                "max_no_volunteer_rounds": 6,
                "max_attempts": 3,
            }
        },
    }
    adapter = MockAdapter()
    engine_module = RUNNER.load_policy_engine(PILOT / "allocation_engine.py")
    output = tmp_path / "output"

    summary = RUNNER.execute_study(
        config=config,
        cases=cases,
        cases_base=tmp_path,
        output=output,
        adapter=adapter,
        policy_engine=engine_module,
    )

    # Three policies x one task = three calls. An invalid all-model benchmark
    # would make six calls because the team contains two models.
    assert len(adapter.calls) == 3
    assert all(call == ("agent_1", "RLLM001") for call in adapter.calls)
    assert len(summary["runs"]) == 3
    for run in summary["runs"]:
        assert run["event_counts"]["claim_win"] == 1
        assert run["event_counts"]["execute"] == 1
        assert run["event_counts"]["verify"] == 1
        calls_path = output / run["run_id"] / "calls.jsonl"
        calls = [json.loads(line) for line in calls_path.read_text(encoding="utf-8").splitlines()]
        assert calls[0]["validator_passed"] is True


def test_adapter_version_drift_is_retried_as_failure(tmp_path: Path) -> None:
    class DriftAdapter:
        def invoke(self, *, model: dict, case: dict, generation: dict) -> dict:
            return {
                "content": "expected",
                "provider_request_id": "drift",
                "exact_model_version": "moving-alias@different",
                "input_tokens": 1,
                "output_tokens": 1,
                "latency_seconds": 0.1,
                "finish_reason": "stop",
            }

    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "validator.py").write_text(VALIDATOR, encoding="utf-8")
    (bundle / "prompt.md").write_text("Return the expected value.", encoding="utf-8")
    cases = [{
        "case_id": "RLLM001",
        "workload": "adult_ml",
        "adjudicated_difficulty": "1",
        "execution_bundle": "bundle",
        "validator_command": "python validator.py --candidate {candidate}",
    }]
    config = {
        "models": [{
            "slot": "agent_1",
            "model_id": "m",
            "exact_version": "m@frozen",
            "ability_profile": {"ml_build": 1, "fix_bug": 1},
            "input_price_per_million_tokens": 1.0,
            "output_price_per_million_tokens": 1.0,
        }],
        "policies": ["CF_FIT", "S3", "CENTRAL_FIT"],
        "paired_seeds": [3000],
        "generation": {"max_api_retries": 0},
        "allocation_engine": {"parameters": {"max_attempts": 1}},
    }
    output = tmp_path / "output"
    engine_module = RUNNER.load_policy_engine(PILOT / "allocation_engine.py")

    with pytest.raises(RuntimeError, match="infrastructure failure"):
        RUNNER.execute_study(
            config=config,
            cases=cases,
            cases_base=tmp_path,
            output=output,
            adapter=DriftAdapter(),
            policy_engine=engine_module,
        )

    invalid = json.loads((output / "CF_FIT__s3000" / "RUN_INVALID.json").read_text())
    assert invalid["status"] == "invalid_infrastructure_failure"
    assert invalid["research_results"] is False


def test_execution_is_concurrent_and_reports_system_metrics(tmp_path: Path) -> None:
    class SlowAdapter:
        def __init__(self) -> None:
            self.lock = threading.Lock()
            self.active = 0
            self.maximum_active = 0

        def invoke(self, *, model: dict, case: dict, generation: dict) -> dict:
            with self.lock:
                self.active += 1
                self.maximum_active = max(self.maximum_active, self.active)
            try:
                time.sleep(0.12)
            finally:
                with self.lock:
                    self.active -= 1
            return {
                "content": "expected",
                "provider_request_id": f"{model['slot']}-{case['case_id']}",
                "exact_model_version": model["exact_version"],
                "input_tokens": 10,
                "output_tokens": 2,
                "latency_seconds": 0.12,
                "finish_reason": "stop",
            }

    cases = []
    for difficulty in (1, 2, 3):
        case_id = f"RLLM00{difficulty}"
        bundle_name = f"bundle_{difficulty}"
        bundle = tmp_path / bundle_name
        bundle.mkdir()
        (bundle / "validator.py").write_text(VALIDATOR, encoding="utf-8")
        (bundle / "prompt.md").write_text("Return the expected value.", encoding="utf-8")
        cases.append({
            "case_id": case_id,
            "workload": "adult_ml",
            "adjudicated_difficulty": str(difficulty),
            "execution_bundle": bundle_name,
            "validator_command": "python validator.py --candidate {candidate}",
        })
    config = {
        "models": [
            {
                "slot": f"agent_{rank}",
                "model_id": f"model_{rank}",
                "exact_version": f"model_{rank}@frozen",
                "ability_profile": {"ml_build": rank, "fix_bug": rank},
                "input_price_per_million_tokens": float(rank),
                "output_price_per_million_tokens": float(rank * 2),
            }
            for rank in (1, 2, 3)
        ],
        "policies": ["CF_FIT", "S3", "CENTRAL_FIT"],
        "paired_seeds": [3000],
        "generation": {"max_api_retries": 0},
        "validator_timeout_seconds": 10,
        "allocation_engine": {"parameters": {"max_attempts": 1}},
    }
    adapter = SlowAdapter()
    engine_module = RUNNER.load_policy_engine(PILOT / "allocation_engine.py")
    output = tmp_path / "output"

    summary = RUNNER.execute_study(
        config=config,
        cases=cases,
        cases_base=tmp_path,
        output=output,
        adapter=adapter,
        policy_engine=engine_module,
    )

    assert adapter.maximum_active >= 2
    assert len(summary["runs"]) == 3
    for run in summary["runs"]:
        assert run["tasks_verified"] == 3
        assert run["completion_rate"] == 1.0
        assert run["maximum_concurrent_executions"] >= 2
        assert 0.0 < run["resource_utilization"] <= 1.0
        assert run["verified_throughput_per_second"] > 0.0
        assert run["p95_verified_completion_time_seconds"] is not None
        assert run["p95_terminal_flow_time_seconds"] is not None
        assert run["cost_per_verified_task"] is not None
