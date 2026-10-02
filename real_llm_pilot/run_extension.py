from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import sys
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adapter_contract import validate_response
from validator_contract import validate_bundle


HERE = Path(__file__).resolve().parent
PLACEHOLDER_VALUES = {
    "FILL_BEFORE_EXECUTION",
    "UNVERIFIED_DEPLOYMENT_ALIAS",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_adapter(path: Path):
    spec = importlib.util.spec_from_file_location("real_llm_provider_adapter", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "invoke"):
        raise ValueError("adapter module must expose invoke(model=, case=, generation=)")
    return module


def load_policy_engine(path: Path):
    spec = importlib.util.spec_from_file_location("real_llm_allocation_engine_extension", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load allocation engine: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    required = {"AllocationEngine", "EngineConfig", "agents_from_config", "tasks_from_manifest"}
    missing = sorted(name for name in required if not hasattr(module, name))
    if missing:
        raise ValueError(f"allocation engine missing exports: {missing}")
    return module


def validate_config(config: dict[str, Any], *, execute: bool) -> None:
    models = config.get("models", [])
    if not 1 <= len(models) <= 4:
        raise ValueError("team must contain 1-4 models")
    slots = [str(model.get("slot", "")) for model in models]
    if any(not slot for slot in slots) or len(set(slots)) != len(slots):
        raise ValueError("each team slot must have a unique non-empty slot id")
    team_design = str(config.get("team_design", ""))
    if "homogeneous" not in team_design.lower():
        versions = [model.get("exact_version") for model in models]
        pinned_versions = [
            version
            for version in versions
            if version
            and version not in PLACEHOLDER_VALUES
            and "ALIAS" not in str(version).upper()
        ]
        if len(set(pinned_versions)) != len(pinned_versions):
            raise ValueError(
                "duplicate exact_version is permitted only for an explicitly homogeneous team"
            )
    if config.get("ability_gate", {}).get("price_is_not_ability") is not True:
        raise ValueError("ability must remain separate from price")
    if execute:
        text = json.dumps(config)
        if "FILL_BEFORE_EXECUTION" in text or config.get("study_status") != "FROZEN_FOR_EXECUTION":
            raise ValueError("execution requires a completed config with study_status=FROZEN_FOR_EXECUTION")
        for model in models:
            static_prices = (
                model.get("input_price_per_million_tokens") is not None
                and model.get("output_price_per_million_tokens") is not None
            )
            provider_cost = model.get("cost_accounting_mode") == "provider_response_header"
            if not static_prices and not provider_cost:
                raise ValueError(
                    "execution requires frozen token prices or provider response-cost accounting"
                )


def collect_preflight_blockers(
    config: dict[str, Any], cases: list[dict[str, Any]], *, cases_path: Path
) -> list[dict[str, Any]]:
    """Return all conditions that prevent a defensible allocation-policy run.

    The legacy scaffold called every model for every case. That is useful for a
    model benchmark, but it is not a ConveyorFlow allocation experiment. Real
    execution therefore remains locked until a frozen allocation engine is
    supplied and every provenance/cost/case prerequisite is complete.
    """

    blockers: list[dict[str, Any]] = []
    if config.get("study_status") != "FROZEN_FOR_EXECUTION":
        blockers.append(
            {
                "code": "CONFIG_NOT_FROZEN",
                "count": 1,
                "detail": "study_status must equal FROZEN_FOR_EXECUTION",
            }
        )

    unpinned = [
        model.get("slot", "unknown")
        for model in config.get("models", [])
        if not model.get("exact_version")
        or model.get("exact_version") in PLACEHOLDER_VALUES
        or "ALIAS" in str(model.get("exact_version", "")).upper()
    ]
    if unpinned:
        blockers.append(
            {
                "code": "MODEL_VERSION_UNPINNED",
                "count": len(unpinned),
                "items": unpinned,
            }
        )

    missing_prices = [
        model.get("slot", "unknown")
        for model in config.get("models", [])
        if (
            model.get("input_price_per_million_tokens") is None
            or model.get("output_price_per_million_tokens") is None
        )
        and model.get("cost_accounting_mode") != "provider_response_header"
    ]
    if missing_prices:
        blockers.append(
            {
                "code": "TOKEN_PRICE_MISSING",
                "count": len(missing_prices),
                "items": missing_prices,
            }
        )

    not_ready = [case.get("case_id", "unknown") for case in cases if str(case.get("executable_ready", "")).lower() != "true"]
    if not_ready:
        blockers.append(
            {
                "code": "CASE_NOT_EXECUTABLE",
                "count": len(not_ready),
                "items": not_ready,
            }
        )

    missing_bundles: list[str] = []
    missing_validators: list[str] = []
    incomplete_bundles: list[str] = []
    for case in cases:
        case_id = case.get("case_id", "unknown")
        bundle = case.get("execution_bundle", "")
        validator = case.get("validator_command", "")
        if not bundle or bundle in PLACEHOLDER_VALUES:
            missing_bundles.append(case_id)
        else:
            bundle_path = (cases_path.parent / bundle).resolve()
            if not bundle_path.exists():
                missing_bundles.append(case_id)
            elif not bundle_path.is_dir() or not all(
                (bundle_path / name).is_file()
                for name in ("prompt.md", "expected.json", "provenance.json", "validator.py")
            ):
                incomplete_bundles.append(case_id)
        if not validator or validator in PLACEHOLDER_VALUES:
            missing_validators.append(case_id)
        elif validator.strip() != "python validator.py --candidate {candidate}":
            missing_validators.append(case_id)
    if missing_bundles:
        blockers.append(
            {
                "code": "EXECUTION_BUNDLE_MISSING",
                "count": len(missing_bundles),
                "items": missing_bundles,
            }
        )
    if missing_validators:
        blockers.append(
            {
                "code": "VALIDATOR_COMMAND_MISSING",
                "count": len(missing_validators),
                "items": missing_validators,
            }
        )
    if incomplete_bundles:
        blockers.append(
            {
                "code": "CASE_BUNDLE_INCOMPLETE",
                "count": len(incomplete_bundles),
                "items": incomplete_bundles,
            }
        )

    case_lock = config.get("case_bundles", {})
    if (
        case_lock.get("status") != "FROZEN_FOR_EXECUTION"
        or not case_lock.get("lock_file")
        or not case_lock.get("sha256")
    ):
        blockers.append(
            {
                "code": "CASE_BUNDLES_NOT_FROZEN",
                "count": 1,
                "detail": "audited bundles and their manifest must have an immutable lock",
            }
        )
    else:
        lock_path = (cases_path.parent / str(case_lock["lock_file"])).resolve()
        if not lock_path.is_file():
            blockers.append({"code": "CASE_BUNDLE_LOCK_MISSING", "count": 1})
        elif sha256(lock_path) != str(case_lock["sha256"]).lower():
            blockers.append({"code": "CASE_BUNDLE_LOCK_HASH_MISMATCH", "count": 1})
        else:
            locked = json.loads(lock_path.read_text(encoding="utf-8"))
            if (
                locked.get("status") != "FROZEN_FOR_EXECUTION"
                or locked.get("case_count") != len(cases)
                or locked.get("manifest_sha256") != sha256(cases_path)
            ):
                blockers.append({"code": "CASE_BUNDLE_LOCK_CONTENT_MISMATCH", "count": 1})

    engine = config.get("allocation_engine", {})
    if (
        engine.get("status") != "FROZEN_FOR_EXECUTION"
        or not engine.get("module")
        or not engine.get("sha256")
    ):
        blockers.append(
            {
                "code": "ALLOCATION_ENGINE_NOT_FROZEN",
                "count": 1,
                "detail": (
                    "A policy engine must implement CF-Fit volunteering/stand-down/aging, "
                    "static round robin, and Central-Fit. Calling every model for every "
                    "case is not an allocation experiment."
                ),
            }
        )
    elif engine.get("module"):
        engine_path = (cases_path.parent / str(engine["module"])).resolve()
        if not engine_path.is_file():
            blockers.append(
                {
                    "code": "ALLOCATION_ENGINE_MODULE_MISSING",
                    "count": 1,
                    "detail": str(engine_path),
                }
            )
        elif sha256(engine_path) != str(engine.get("sha256", "")).lower():
            blockers.append(
                {
                    "code": "ALLOCATION_ENGINE_HASH_MISMATCH",
                    "count": 1,
                    "detail": "allocation engine differs from the frozen SHA-256",
                }
            )
    return blockers


def load_cases(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def _percentile(values: list[float], quantile: float) -> float | None:
    """Return a deterministic nearest-rank percentile for an empirical sample."""

    if not values:
        return None
    if not 0 < quantile <= 1:
        raise ValueError("quantile must be in (0, 1]")
    ordered = sorted(float(value) for value in values)
    return ordered[max(0, math.ceil(quantile * len(ordered)) - 1)]


def _maximum_overlap(intervals: list[tuple[float, float]]) -> int:
    """Return peak simultaneous executions; an ending call frees capacity first."""

    points: list[tuple[float, int]] = []
    for started, ended in intervals:
        points.append((float(started), 1))
        points.append((float(ended), -1))
    active = 0
    maximum = 0
    for _timestamp, delta in sorted(points, key=lambda value: (value[0], value[1])):
        active += delta
        maximum = max(maximum, active)
    return maximum


def execute_study(
    *,
    config: dict[str, Any],
    cases: list[dict[str, Any]],
    cases_base: Path,
    output: Path,
    adapter: Any,
    policy_engine: Any,
    selected_seeds: list[int] | None = None,
    selected_policies: list[str] | None = None,
) -> dict[str, Any]:
    """Execute atomic claim winners concurrently and preserve full provenance.

    Allocation remains single-threaded and auditable.  Provider calls plus
    deterministic validation run in worker threads, one active task per agent.
    A completed agent returns to the belt immediately; the scheduler does not
    wait for the other agents in that allocation round.
    """

    frozen_seeds = [int(seed) for seed in config.get("paired_seeds", [])]
    seeds = selected_seeds if selected_seeds is not None else frozen_seeds
    if not seeds:
        raise ValueError("paired_seeds must be frozen before execution")
    if any(seed not in frozen_seeds for seed in seeds):
        raise ValueError("selected seed is not part of the frozen paired_seeds")
    frozen_policies = list(config.get("policies", []))
    allowed_extension_policies = {"CF_FIT", "CF_FIT_NO_STANDDOWN"}
    if len(frozen_policies) != 1 or frozen_policies[0] not in allowed_extension_policies:
        raise ValueError("extension config must freeze exactly one CF-Fit variant")
    policies = selected_policies if selected_policies is not None else frozen_policies
    if not policies or any(policy not in frozen_policies for policy in policies):
        raise ValueError("selected policy is not part of the frozen policy set")
    engine_parameters = config["allocation_engine"].get("parameters", {})
    engine_config = policy_engine.EngineConfig(**engine_parameters)
    agents = policy_engine.agents_from_config(config)
    task_specs = policy_engine.tasks_from_manifest(cases)
    models = {str(model["slot"]): model for model in config["models"]}
    cases_by_id = {str(case["case_id"]): case for case in cases}
    generation = config["generation"]
    max_api_retries = int(generation.get("max_api_retries", 0))
    validator_timeout = int(config.get("validator_timeout_seconds", 120))
    run_summaries: list[dict[str, Any]] = []

    for seed in seeds:
        for policy in policies:
            run_id = f"{policy}__s{seed}"
            run_root = output / run_id
            run_root.mkdir(parents=True, exist_ok=False)
            engine = policy_engine.AllocationEngine(
                policy=policy,
                agents=agents,
                tasks=task_specs,
                seed=seed,
                config=engine_config,
            )
            call_rows: list[dict[str, Any]] = []
            scheduler_rounds = 0
            run_started = time.perf_counter()
            terminal_offsets: dict[str, float] = {}
            busy_seconds_by_agent = {agent.agent_id: 0.0 for agent in agents}
            execution_intervals: list[tuple[float, float]] = []
            queue_waits: list[float] = []

            def execute_assignment(assignment: Any, queued_at: float) -> dict[str, Any]:
                started_at = time.perf_counter()
                started_offset = started_at - run_started
                case = cases_by_id[assignment.task_id]
                model = models[assignment.agent_id]
                bundle_path = (cases_base / str(case["execution_bundle"])).resolve()
                prompt_path = bundle_path / "prompt.md"
                if not prompt_path.is_file():
                    raise ValueError(f"prompt.md missing for {assignment.task_id}")
                adapter_case = dict(case)
                adapter_case["prompt"] = prompt_path.read_text(encoding="utf-8")
                response: dict[str, Any] | None = None
                error_text: str | None = None
                successful_api_try = 0
                local_rows: list[dict[str, Any]] = []
                for api_try in range(max_api_retries + 1):
                    try:
                        candidate = adapter.invoke(
                            model=model,
                            case=adapter_case,
                            generation=generation,
                        )
                        validate_response(candidate)
                        if candidate["exact_model_version"] != model["exact_version"]:
                            raise ValueError(
                                "adapter returned a model version different from the frozen version"
                            )
                        response = candidate
                        successful_api_try = api_try + 1
                        error_text = None
                        break
                    except Exception as exc:  # adapter boundary is intentionally broad
                        error_text = f"{type(exc).__name__}: {exc}"
                        local_rows.append(
                            {
                                "run_id": run_id,
                                "task_id": assignment.task_id,
                                "agent_id": assignment.agent_id,
                                "attempt": assignment.attempt,
                                "api_try": api_try + 1,
                                "status": "adapter_error",
                                "error": error_text,
                            }
                        )

                if response is None:
                    ended_offset = time.perf_counter() - run_started
                    metadata = {
                        "status": "adapter_error",
                        "error": error_text,
                        "billable": False,
                        "scheduled_offset_seconds": queued_at,
                        "started_offset_seconds": started_offset,
                        "ended_offset_seconds": ended_offset,
                    }
                    return {
                        "assignment": assignment,
                        "passed": False,
                        "metadata": metadata,
                        "call_rows": local_rows,
                        "started_offset": started_offset,
                        "ended_offset": ended_offset,
                    }

                content = str(response["content"])
                attempt_path = (
                    run_root / "attempts" / f"{assignment.task_id}__a{assignment.attempt}"
                )
                validation = validate_bundle(
                    bundle_path=bundle_path,
                    validator_command=str(case["validator_command"]),
                    candidate_content=content,
                    work_path=attempt_path,
                    timeout_seconds=validator_timeout,
                )
                ended_offset = time.perf_counter() - run_started
                input_tokens = int(response["input_tokens"])
                output_tokens = int(response["output_tokens"])
                if model.get("cost_accounting_mode") == "provider_response_header":
                    if response.get("response_cost") is None:
                        raise ValueError(
                            "MFEC response omitted x-litellm-response-cost required by frozen config"
                        )
                    cost = float(response["response_cost"])
                    cost_source = "x-litellm-response-cost"
                else:
                    cost = (
                        input_tokens * float(model["input_price_per_million_tokens"])
                        + output_tokens * float(model["output_price_per_million_tokens"])
                    ) / 1_000_000
                    cost_source = "frozen_token_prices"
                metadata = {
                    "status": "completed",
                    "provider_request_id": response["provider_request_id"],
                    "exact_model_version": response["exact_model_version"],
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "latency_seconds": float(response["latency_seconds"]),
                    "finish_reason": response["finish_reason"],
                    "output_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    "cost": cost,
                    "cost_source": cost_source,
                    "billable": True,
                    "validator_exit_code": validation["validator_exit_code"],
                    "scheduled_offset_seconds": queued_at,
                    "started_offset_seconds": started_offset,
                    "ended_offset_seconds": ended_offset,
                }
                local_rows.append(
                    {
                        "run_id": run_id,
                        "task_id": assignment.task_id,
                        "agent_id": assignment.agent_id,
                        "attempt": assignment.attempt,
                        "api_try": successful_api_try,
                        **metadata,
                        "validator_passed": validation["passed"],
                    }
                )
                return {
                    "assignment": assignment,
                    "passed": bool(validation["passed"]),
                    "metadata": metadata,
                    "call_rows": local_rows,
                    "started_offset": started_offset,
                    "ended_offset": ended_offset,
                }

            active: dict[Future[dict[str, Any]], Any] = {}
            with ThreadPoolExecutor(max_workers=len(agents)) as executor:
                while not engine.terminal or active:
                    assignments = [] if engine.terminal else engine.allocate_round()
                    if not engine.terminal:
                        scheduler_rounds += 1
                    queued_at = time.perf_counter() - run_started
                    for assignment in assignments:
                        future = executor.submit(execute_assignment, assignment, queued_at)
                        active[future] = assignment

                    if scheduler_rounds > 10_000 and not engine.terminal:
                        engine.mark_unsettled()

                    if active:
                        done, _pending = wait(active, return_when=FIRST_COMPLETED)
                        finished: list[tuple[Future[dict[str, Any]], dict[str, Any]]] = []
                        for future in done:
                            finished.append((future, future.result()))
                        finished.sort(
                            key=lambda item: (
                                float(item[1]["ended_offset"]),
                                item[1]["assignment"].task_id,
                            )
                        )
                        for future, result in finished:
                            active.pop(future)
                            assignment = result["assignment"]
                            started_offset = float(result["started_offset"])
                            ended_offset = float(result["ended_offset"])
                            call_rows.extend(result["call_rows"])
                            if result["metadata"].get("status") == "adapter_error":
                                _write_jsonl(run_root / "calls.partial.jsonl", call_rows)
                                invalid = {
                                    "status": "invalid_infrastructure_failure",
                                    "research_results": False,
                                    "run_id": run_id,
                                    "task_id": assignment.task_id,
                                    "agent_id": assignment.agent_id,
                                    "error": result["metadata"].get("error"),
                                    "rule": (
                                        "Provider failure after max_api_retries aborts the policy; "
                                        "it is never counted as a task-quality failure."
                                    ),
                                }
                                (run_root / "RUN_INVALID.json").write_text(
                                    json.dumps(invalid, indent=2) + "\n", encoding="utf-8"
                                )
                                raise RuntimeError(
                                    f"infrastructure failure in {run_id}: {invalid['error']}"
                                )
                            execution_intervals.append((started_offset, ended_offset))
                            busy_seconds_by_agent[assignment.agent_id] += max(
                                0.0, ended_offset - started_offset
                            )
                            queue_waits.append(
                                max(
                                    0.0,
                                    started_offset
                                    - float(result["metadata"]["scheduled_offset_seconds"]),
                                )
                            )
                            engine.complete(
                                assignment,
                                passed=bool(result["passed"]),
                                execution_metadata=result["metadata"],
                            )
                            state = engine.tasks[assignment.task_id].status
                            if state in {"VERIFIED", "DEAD_LETTER", "UNSETTLED"}:
                                terminal_offsets[assignment.task_id] = ended_offset
                    elif engine.terminal:
                        break

                    now_offset = time.perf_counter() - run_started
                    for task_id, state in engine.tasks.items():
                        if (
                            state.status in {"VERIFIED", "DEAD_LETTER", "UNSETTLED"}
                            and task_id not in terminal_offsets
                        ):
                            terminal_offsets[task_id] = now_offset

            run_wall_time = time.perf_counter() - run_started

            _write_jsonl(run_root / "events.jsonl", engine.events)
            _write_jsonl(run_root / "calls.jsonl", call_rows)
            event_counts: dict[str, int] = {}
            for event in engine.events:
                name = str(event["event"])
                event_counts[name] = event_counts.get(name, 0) + 1
            completed_calls = [row for row in call_rows if row["status"] == "completed"]
            statuses = {task_id: state.status for task_id, state in engine.tasks.items()}
            verified_ids = [task_id for task_id, status in statuses.items() if status == "VERIFIED"]
            dead_letter_ids = [task_id for task_id, status in statuses.items() if status == "DEAD_LETTER"]
            unsettled_ids = [task_id for task_id, status in statuses.items() if status == "UNSETTLED"]
            verified_completion_times = [
                terminal_offsets[task_id] for task_id in verified_ids if task_id in terminal_offsets
            ]
            terminal_flow_times = [
                terminal_offsets[task_id]
                for task_id in statuses
                if task_id in terminal_offsets
            ]
            total_cost = sum(float(row["cost"]) for row in completed_calls)
            total_busy = sum(busy_seconds_by_agent.values())
            summary = {
                "run_id": run_id,
                "seed": seed,
                "policy": policy,
                "event_hash": engine.event_hash,
                "scheduler_rounds": scheduler_rounds,
                "event_counts": event_counts,
                "tasks_total": len(statuses),
                "tasks_verified": len(verified_ids),
                "tasks_dead_letter": len(dead_letter_ids),
                "tasks_unsettled": len(unsettled_ids),
                "completion_rate": len(verified_ids) / len(statuses) if statuses else 0.0,
                "provider_calls_completed": len(completed_calls),
                "input_tokens": sum(int(row["input_tokens"]) for row in completed_calls),
                "output_tokens": sum(int(row["output_tokens"]) for row in completed_calls),
                "total_cost": total_cost,
                "total_latency_seconds": sum(
                    float(row["latency_seconds"]) for row in completed_calls
                ),
                "run_wall_time_seconds": run_wall_time,
                "verified_throughput_per_second": (
                    len(verified_ids) / run_wall_time if run_wall_time > 0 else 0.0
                ),
                "resource_utilization": (
                    total_busy / (run_wall_time * len(agents))
                    if run_wall_time > 0 and agents
                    else 0.0
                ),
                "busy_seconds_by_agent": busy_seconds_by_agent,
                "maximum_concurrent_executions": _maximum_overlap(execution_intervals),
                "mean_attempt_queue_wait_seconds": (
                    sum(queue_waits) / len(queue_waits) if queue_waits else 0.0
                ),
                "p95_verified_completion_time_seconds": _percentile(
                    verified_completion_times, 0.95
                ),
                "p95_terminal_flow_time_seconds": _percentile(terminal_flow_times, 0.95),
                "cost_per_verified_task": (
                    total_cost / len(verified_ids) if verified_ids else None
                ),
            }
            (run_root / "summary.json").write_text(
                json.dumps(summary, indent=2) + "\n", encoding="utf-8"
            )
            run_summaries.append(summary)

    study_summary = {
        "status": "execution_complete",
        "research_results": True,
        "evidence_phase": "supplementary_real_llm_extension",
        "condition_id": config.get("condition_id"),
        "execution_mode": "concurrent_non_barrier",
        "metric_clock": "monotonic_wall_clock",
        "paired_seeds": seeds,
        "policies": policies,
        "runs": run_summaries,
    }
    (output / "study_summary.json").write_text(
        json.dumps(study_summary, indent=2) + "\n", encoding="utf-8"
    )
    return study_summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate or execute the frozen ConveyorFlow Real-LLM supplementary extension.")
    parser.add_argument("--config", type=Path, default=HERE / "config.template.json")
    parser.add_argument("--cases", type=Path, default=HERE / "case_manifest.csv")
    parser.add_argument("--output", type=Path, default=HERE / "pilot_output")
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--only-seed",
        action="append",
        type=int,
        help="Execute only this frozen paired seed; may be repeated for staged Main runs.",
    )
    parser.add_argument(
        "--seed-from",
        type=int,
        help="Execute frozen paired seeds greater than or equal to this value.",
    )
    parser.add_argument(
        "--only-policy",
        action="append",
        choices=("CF_FIT", "CF_FIT_NO_STANDDOWN"),
        help="Execute only this frozen policy; may be repeated for staged Main runs.",
    )
    args = parser.parse_args()
    if not args.dry_run and args.adapter is None:
        raise SystemExit("real execution requires --adapter; use --dry-run for validation only")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    cases = load_cases(args.cases)
    execute = not args.dry_run
    validate_config(config, execute=False)
    if len(cases) != 60 or len({case["case_id"] for case in cases}) != 60:
        raise ValueError("case manifest must contain 60 unique cases")
    counts: dict[str, int] = {}
    for case in cases:
        counts[case["workload"]] = counts.get(case["workload"], 0) + 1
    if counts != {"adult_ml": 20, "beijing_ml": 20, "bugs2fix": 20}:
        raise ValueError(f"unexpected workload balance: {counts}")
    blockers = collect_preflight_blockers(config, cases, cases_path=args.cases)
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "blocked_not_executed" if blockers else "ready_not_executed",
        "research_results": False,
        "config_sha256": sha256(args.config),
        "cases_sha256": sha256(args.cases),
        "models": len(config["models"]),
        "cases": len(cases),
        "workload_counts": counts,
        "blockers": blockers,
    }
    if args.dry_run:
        destination = args.output / "dry_run_manifest.json"
        destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(manifest, indent=2))
        return 0

    if blockers:
        codes = ", ".join(blocker["code"] for blocker in blockers)
        raise ValueError(f"real execution blocked by preflight: {codes}")

    validate_config(config, execute=True)
    adapter = load_adapter(args.adapter)
    engine_path = (args.cases.parent / config["allocation_engine"]["module"]).resolve()
    policy_engine = load_policy_engine(engine_path)
    execution_output = args.output / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    execution_output.mkdir(parents=True, exist_ok=False)
    selected_seeds = args.only_seed
    if args.seed_from is not None:
        if selected_seeds is not None:
            raise ValueError("--only-seed and --seed-from are mutually exclusive")
        selected_seeds = [
            int(seed) for seed in config.get("paired_seeds", []) if int(seed) >= args.seed_from
        ]
    study_summary = execute_study(
        config=config,
        cases=cases,
        cases_base=args.cases.parent,
        output=execution_output,
        adapter=adapter,
        policy_engine=policy_engine,
        selected_seeds=selected_seeds,
        selected_policies=args.only_policy,
    )
    print(json.dumps(study_summary, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
