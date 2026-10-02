from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

from run_pilot import (
    ROOT,
    RunConfig,
    execute_one,
    read_partial,
    source_hash,
    write_csv,
)


ABLATIONS = {
    "FULL": {},
    "A1": {"no_assess": True},
    "A2": {"no_fit": True},
    "A3": {"no_standdown": True},
    "A4": {"no_aging": True},
}


def build_design(settings: dict, smoke: bool) -> tuple[list[RunConfig], dict[str, set[str]]]:
    seed_start = int(settings["seed_start"])
    seeds = range(seed_start, seed_start + (1 if smoke else int(settings["seeds"])))
    workloads = settings["workloads"]
    loads = (
        {"medium": settings["loads"]["medium"]}
        if smoke
        else settings["loads"]
    )
    shared = {
        "n_jobs": 12 if smoke else int(settings["n_jobs"]),
        "k_scan": int(settings["k_scan"]),
        "max_attempts": int(settings["max_attempts"]),
        "w1": int(settings["w1"]),
        "w2": int(settings["w2"]),
        "w3": int(settings["w3"]),
        "requeue_limit": int(settings["requeue_limit"]),
        "drain_ticks": 80 if smoke else int(settings["drain_ticks"]),
    }
    configs: dict[str, RunConfig] = {}
    scopes: dict[str, set[str]] = {}

    def add(config: RunConfig, scope: str) -> None:
        existing = configs.get(config.run_id)
        if existing is not None and asdict(existing) != asdict(config):
            raise AssertionError(f"run-id collision: {config.run_id}")
        configs[config.run_id] = config
        scopes.setdefault(config.run_id, set()).add(scope)

    rq3_teams = ["H1"] if smoke else settings["rq3_teams"]
    rq3_regimes = ["R0"] if smoke else settings["rq3_regimes"]
    for seed in seeds:
        for workload in workloads:
            for load_name, rho in loads.items():
                for team in rq3_teams:
                    for regime in rq3_regimes:
                        for ablation in settings["ablations"]:
                            add(
                                RunConfig(
                                    seed=seed,
                                    strategy="CF_FIT",
                                    workload=workload,
                                    load_name=load_name,
                                    rho=float(rho),
                                    team=team,
                                    resource_regime=regime,
                                    fallback="F2",
                                    difficulty_profile="mixed",
                                    **ABLATIONS[ablation],
                                    **shared,
                                ),
                                "RQ3",
                            )

    sensitivity_teams = ["H1"] if smoke else settings["rq3_teams"]
    for seed in seeds:
        for workload in workloads:
            for load_name, rho in loads.items():
                for team in sensitivity_teams:
                    for regime in settings["sensitivity_regimes"]:
                        add(
                            RunConfig(
                                seed=seed,
                                strategy="CF_FIT",
                                workload=workload,
                                load_name=load_name,
                                rho=float(rho),
                                team=team,
                                resource_regime=regime,
                                fallback="F2",
                                difficulty_profile="mixed",
                                **shared,
                            ),
                            "RESOURCE_SENSITIVITY",
                        )

    e4_regimes = ["R0"] if smoke else settings["e4_regimes"]
    for seed in seeds:
        for workload in workloads:
            for load_name, rho in loads.items():
                for team in settings["e4_teams"]:
                    for regime in e4_regimes:
                        for profile in settings["difficulty_profiles"]:
                            for fallback in settings["fallbacks"]:
                                add(
                                    RunConfig(
                                        seed=seed,
                                        strategy="CF_FIT",
                                        workload=workload,
                                        load_name=load_name,
                                        rho=float(rho),
                                        team=team,
                                        resource_regime=regime,
                                        fallback=fallback,
                                        difficulty_profile=profile,
                                        **shared,
                                    ),
                                    "E4",
                                )
    return [configs[key] for key in sorted(configs)], scopes


def main() -> int:
    parser = argparse.ArgumentParser(description="Run frozen RQ3/E4 pre-main pilot extensions.")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    args = parser.parse_args()
    settings = json.loads(
        (ROOT / "config" / "pilot_extensions.json").read_text(encoding="utf-8")
    )
    design, scopes = build_design(settings, args.smoke)
    if not args.smoke and len(design) != int(settings["expected_unique_runs"]):
        raise AssertionError(
            f"frozen design expected {settings['expected_unique_runs']}, got {len(design)}"
        )
    output = ROOT / "results" / ("pilot_extensions_smoke" if args.smoke else "pilot_extensions")
    event_dir = output / "events"
    output.mkdir(parents=True, exist_ok=True)
    design_rows = [
        {
            "run_id": item.run_id,
            "pilot_extension_scopes": ";".join(sorted(scopes[item.run_id])),
            **asdict(item),
        }
        for item in design
    ]
    write_csv(output / "design.csv", design_rows)
    metadata = {
        "kind": "PILOT_EXTENSION_SMOKE" if args.smoke else "PILOT_EXTENSION",
        "not_main_experiment": True,
        "preregistration": "docs/PILOT_EXTENSION_PREREGISTRATION.md",
        "created_unix": time.time(),
        "source_sha256": source_hash(),
        "settings": settings,
        "expected_runs": len(design),
    }
    (output / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    partial = output / "metrics.partial.jsonl"
    completed = read_partial(partial)
    pending = [item for item in design if item.run_id not in completed]
    print(
        f"{metadata['kind']}: {len(design)} total, {len(completed)} resumed, "
        f"{len(pending)} pending",
        flush=True,
    )
    started = time.time()
    if pending:
        with partial.open("a", encoding="utf-8", newline="\n") as handle:
            with ProcessPoolExecutor(max_workers=max(1, args.workers)) as executor:
                futures = {
                    executor.submit(
                        execute_one, (asdict(item), str(ROOT), str(event_dir))
                    ): item.run_id
                    for item in pending
                }
                for index, future in enumerate(as_completed(futures), start=1):
                    run_id = futures[future]
                    row = future.result()
                    row["pilot_extension_scopes"] = ";".join(sorted(scopes[run_id]))
                    completed[run_id] = row
                    handle.write(json.dumps(row, sort_keys=True, allow_nan=True) + "\n")
                    handle.flush()
                    if index == 1 or index % 100 == 0 or index == len(pending):
                        print(
                            f"completed {index}/{len(pending)} pending runs in "
                            f"{time.time() - started:.1f}s",
                            flush=True,
                        )
    ordered = [completed[item.run_id] for item in design]
    write_csv(output / "metrics.csv", ordered)
    summary = {
        "status": "complete",
        "kind": metadata["kind"],
        "run_count": len(ordered),
        "expected_run_count": len(design),
        "unique_run_ids": len({row["run_id"] for row in ordered}),
        "source_sha256": metadata["source_sha256"],
        "elapsed_seconds_this_invocation": time.time() - started,
    }
    (output / "execution_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
