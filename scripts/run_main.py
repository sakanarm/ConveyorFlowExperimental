from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

from run_pilot import ROOT, RunConfig, execute_one, read_partial, source_hash, write_csv


ABLATIONS = {
    "FULL": {},
    "A1": {"no_assess": True},
    "A2": {"no_fit": True},
    "A3": {"no_standdown": True},
    "A4": {"no_aging": True},
}


def build_design(settings: dict) -> tuple[list[RunConfig], dict[str, set[str]]]:
    seeds = range(int(settings["seed_start"]), int(settings["seed_start"]) + int(settings["seeds"]))
    workloads = settings["workloads"]
    loads = settings["loads"]
    shared = {
        "n_jobs": int(settings["n_jobs"]),
        "k_scan": int(settings["k_scan"]),
        "max_attempts": int(settings["max_attempts"]),
        "w1": int(settings["w1"]),
        "w2": int(settings["w2"]),
        "w3": int(settings["w3"]),
        "requeue_limit": int(settings["requeue_limit"]),
        "drain_ticks": int(settings["drain_ticks"]),
        "difficulty_source": "frozen_llm",
    }
    configs: dict[str, RunConfig] = {}
    scopes: dict[str, set[str]] = {}

    def add(item: RunConfig, scope: str) -> None:
        prior = configs.get(item.run_id)
        if prior is not None and asdict(prior) != asdict(item):
            raise AssertionError(f"run-id collision: {item.run_id}")
        configs[item.run_id] = item
        scopes.setdefault(item.run_id, set()).add(scope)

    for seed in seeds:
        for workload in workloads:
            for load_name, rho in loads.items():
                for regime in settings["primary_resource_regimes"]:
                    for strategy in settings["rq1_strategies"]:
                        add(
                            RunConfig(
                                seed=seed, strategy=strategy, workload=workload,
                                load_name=load_name, rho=float(rho), team="H1",
                                resource_regime=regime, **shared,
                            ),
                            "RQ1",
                        )
                    for team in settings["rq2_teams"]:
                        add(
                            RunConfig(
                                seed=seed, strategy="CF_FIT", workload=workload,
                                load_name=load_name, rho=float(rho), team=team,
                                resource_regime=regime, **shared,
                            ),
                            "RQ2",
                        )

    for seed in seeds:
        for workload in workloads:
            for load_name in settings["rq3_loads"]:
                rho = float(loads[load_name])
                for team in settings["rq3_teams"]:
                    for regime in settings["primary_resource_regimes"]:
                        for ablation in settings["ablations"]:
                            add(
                                RunConfig(
                                    seed=seed, strategy="CF_FIT", workload=workload,
                                    load_name=load_name, rho=rho, team=team,
                                    resource_regime=regime, **ABLATIONS[ablation], **shared,
                                ),
                                "RQ3",
                            )

    for seed in seeds:
        for workload in workloads:
            for load_name in settings["e4_loads"]:
                rho = float(loads[load_name])
                for team in settings["e4_teams"]:
                    for regime in settings["primary_resource_regimes"]:
                        for profile in settings["difficulty_profiles"]:
                            for fallback in settings["fallbacks"]:
                                add(
                                    RunConfig(
                                        seed=seed, strategy="CF_FIT", workload=workload,
                                        load_name=load_name, rho=rho, team=team,
                                        resource_regime=regime, fallback=fallback,
                                        difficulty_profile=profile, **shared,
                                    ),
                                    "E4",
                                )

    for seed in seeds:
        for workload in workloads:
            for load_name in settings["rq3_loads"]:
                for regime in settings["resource_sensitivity_regimes"]:
                    add(
                        RunConfig(
                            seed=seed, strategy="CF_FIT", workload=workload,
                            load_name=load_name, rho=float(loads[load_name]), team="H1",
                            resource_regime=regime, **shared,
                        ),
                        "RESOURCE_SENSITIVITY",
                    )

    for seed in seeds:
        for workload in workloads:
            for load_name in settings["rq3_loads"]:
                for source in settings["annotation_sensitivity_sources"]:
                    for strategy in settings["annotation_sensitivity_strategies"]:
                        sensitivity = dict(shared)
                        sensitivity["difficulty_source"] = source
                        add(
                            RunConfig(
                                seed=seed, strategy=strategy, workload=workload,
                                load_name=load_name, rho=float(loads[load_name]), team="H1",
                                resource_regime="R0", **sensitivity,
                            ),
                            "ANNOTATION_SENSITIVITY",
                        )
    return [configs[key] for key in sorted(configs)], scopes


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_main_ready(settings: dict) -> dict:
    lock = json.loads((ROOT / "config" / "main_lock.json").read_text(encoding="utf-8"))
    expected = {
        "status": "FROZEN",
        "main_execution_authorized": True,
        "analysis_plan_frozen": True,
    }
    failures = [key for key, value in expected.items() if lock.get(key) != value]
    if not lock.get("execution_authorization", {}).get("recorded"):
        failures.append("execution_authorization.recorded")
    if not lock["llm_annotations"]["agreement_gate_passed"]:
        failures.append("llm_annotations.agreement_gate_passed")
    if not lock["margins"]["approved"]:
        failures.append("margins.approved")
    if lock["sample_size"]["final_paired_seeds"] != int(settings["seeds"]):
        failures.append("sample_size.final_paired_seeds")
    label = ROOT / "expert_labels" / "llm_difficulty_labels_frozen.csv"
    if not label.exists() or sha256(label) != lock["llm_annotations"]["frozen_file_sha256"]:
        failures.append("llm_annotations.frozen_file_sha256")
    if failures:
        raise SystemExit("MAIN BLOCKED; unresolved readiness checks: " + ", ".join(failures))
    return lock


def main() -> int:
    parser = argparse.ArgumentParser(description="Run frozen ConveyorFlow Main simulation.")
    parser.add_argument("--check-design", action="store_true")
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    args = parser.parse_args()
    settings = json.loads((ROOT / "config" / "main_draft.json").read_text(encoding="utf-8"))
    design, scopes = build_design(settings)
    if len(design) != int(settings["expected_unique_runs"]):
        raise AssertionError(f"expected {settings['expected_unique_runs']} unique runs, got {len(design)}")
    if args.check_design:
        counts = {scope: sum(scope in values for values in scopes.values()) for scope in sorted({s for v in scopes.values() for s in v})}
        print(json.dumps({"unique_runs": len(design), "scope_memberships": counts}, indent=2))
        return 0

    lock = assert_main_ready(settings)
    output = ROOT / "results" / "main"
    event_dir = output / "events"
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "design.csv", [{"run_id": item.run_id, "scopes": ";".join(sorted(scopes[item.run_id])), **asdict(item)} for item in design])
    metadata = {
        "kind": "MAIN_CONFIRMATORY",
        "created_unix": time.time(),
        "source_sha256": source_hash(),
        "settings": settings,
        "main_lock": lock,
        "main_lock_sha256": sha256(ROOT / "config" / "main_lock.json"),
        "expected_runs": len(design),
    }
    (output / "run_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    partial = output / "metrics.partial.jsonl"
    completed = read_partial(partial)
    pending = [item for item in design if item.run_id not in completed]
    print(f"MAIN: {len(design)} total, {len(completed)} resumed, {len(pending)} pending", flush=True)
    started = time.time()
    if pending:
        with partial.open("a", encoding="utf-8", newline="\n") as handle:
            with ProcessPoolExecutor(max_workers=max(1, args.workers)) as executor:
                futures = {executor.submit(execute_one, (asdict(item), str(ROOT), str(event_dir))): item.run_id for item in pending}
                for index, future in enumerate(as_completed(futures), start=1):
                    run_id = futures[future]
                    row = future.result()
                    row["main_scopes"] = ";".join(sorted(scopes[run_id]))
                    completed[run_id] = row
                    handle.write(json.dumps(row, sort_keys=True, allow_nan=True) + "\n")
                    handle.flush()
                    if index == 1 or index % 100 == 0 or index == len(pending):
                        print(f"completed {index}/{len(pending)} pending runs in {time.time() - started:.1f}s", flush=True)
    ordered = [completed[item.run_id] for item in design]
    write_csv(output / "metrics.csv", ordered)
    summary = {"status": "complete", "kind": "MAIN_CONFIRMATORY", "run_count": len(ordered), "unique_run_ids": len({row['run_id'] for row in ordered}), "source_sha256": metadata["source_sha256"], "elapsed_seconds_this_invocation": time.time() - started}
    (output / "execution_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
