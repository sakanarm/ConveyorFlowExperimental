"""Run an offline, non-empirical audit of the Real-LLM allocation engine."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from allocation_engine import AllocationEngine, agents_from_config, tasks_from_manifest


HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cases(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def audit_policy(policy: str, config: dict, cases: list[dict[str, str]], seed: int) -> dict:
    engine = AllocationEngine(
        policy=policy,
        agents=agents_from_config(config),
        tasks=tasks_from_manifest(cases),
        seed=seed,
    )
    safety_rounds = 0
    while not engine.terminal:
        assignments = engine.allocate_round()
        for assignment in assignments:
            # This is deliberately a mock validator result. No provider is
            # called and the output is not Real-LLM research evidence.
            engine.complete(
                assignment,
                passed=True,
                execution_metadata={"adapter": "offline_mock", "billable": False},
            )
        safety_rounds += 1
        if safety_rounds > 1000:
            raise RuntimeError(f"{policy} did not terminate")

    counts = Counter(event["event"] for event in engine.events)
    claimants = Counter(
        event["agent_id"] for event in engine.events if event["event"] == "claim_win"
    )
    executed_by_task = Counter(
        event["task_id"] for event in engine.events if event["event"] == "execute"
    )
    invariant_checks = {
        "all_60_tasks_claimed_once": counts["claim_win"] == 60,
        "all_60_tasks_executed_once": counts["execute"] == 60
        and set(executed_by_task.values()) == {1},
        "all_60_tasks_verified": counts["verify"] == 60,
        "one_execute_per_claim_win": counts["execute"] == counts["claim_win"],
        "no_provider_call": True,
        "static_has_no_assessment": policy != "S3" or counts["assessment"] == 0,
        "cf_has_local_volunteers": policy != "CF_FIT"
        or all(
            event.get("local_decision") is True
            for event in engine.events
            if event["event"] == "volunteer"
        ),
        "central_uses_global_matcher": policy != "CENTRAL_FIT"
        or all(
            event.get("selected_by") == "global_matcher"
            for event in engine.events
            if event["event"] == "volunteer"
        ),
    }
    if not all(invariant_checks.values()):
        raise AssertionError({policy: invariant_checks})
    return {
        "policy": policy,
        "seed": seed,
        "rounds": safety_rounds,
        "event_hash": engine.event_hash,
        "event_counts": dict(sorted(counts.items())),
        "claimants": dict(sorted(claimants.items())),
        "invariant_checks": invariant_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=HERE / "config.mfec_final_team.json")
    parser.add_argument("--cases", type=Path, default=HERE / "case_manifest.csv")
    parser.add_argument("--output", type=Path, default=HERE / "allocation_engine_audit.json")
    parser.add_argument("--seed", type=int, default=3000)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    cases = load_cases(args.cases)
    policies = config.get("policies", [])
    if set(policies) != {"CF_FIT", "S3", "CENTRAL_FIT"}:
        raise ValueError("audit requires exactly CF_FIT, S3, and CENTRAL_FIT")
    results = [audit_policy(policy, config, cases, args.seed) for policy in policies]
    output = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "offline_engine_audit_passed",
        "research_results": False,
        "provider_calls": 0,
        "note": "Mock-pass control-flow audit only; not empirical LLM evidence.",
        "engine_sha256": sha256(HERE / "allocation_engine.py"),
        "config_sha256": sha256(args.config),
        "cases_sha256": sha256(args.cases),
        "policies": results,
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
