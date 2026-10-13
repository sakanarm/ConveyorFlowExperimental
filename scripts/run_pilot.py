from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Code"))

from conveyorflow_v2 import RunConfig, run_simulation  # noqa: E402


def build_design(settings: dict, smoke: bool) -> list[RunConfig]:
    seed_start = int(settings.get("seed_start", 0))
    seeds = range(seed_start, seed_start + (2 if smoke else int(settings["seeds"])))
    n_jobs = 12 if smoke else int(settings["n_jobs"])
    workloads = settings["workloads"] if not smoke else settings["workloads"]
    loads = settings["loads"] if not smoke else {"medium": settings["loads"]["medium"]}
    regimes = settings["resource_regimes"] if not smoke else ["R0"]
    shared = {
        "n_jobs": n_jobs,
        "k_scan": int(settings["k_scan"]),
        "max_attempts": int(settings["max_attempts"]),
        "w1": int(settings["w1"]),
        "w2": int(settings["w2"]),
        "w3": int(settings["w3"]),
        "requeue_limit": int(settings["requeue_limit"]),
        "drain_ticks": 80 if smoke else int(settings["drain_ticks"]),
    }
    design: list[RunConfig] = []
    # RQ1: the same H1 team under all policies and both resource regimes.
    for seed in seeds:
        for workload in workloads:
            for load_name, rho in loads.items():
                for regime in regimes:
                    for strategy in settings["strategies"]:
                        design.append(
                            RunConfig(
                                seed=seed,
                                strategy=strategy,
                                workload=workload,
                                load_name=load_name,
                                rho=float(rho),
                                team="H1",
                                resource_regime=regime,
                                **shared,
                            )
                        )
    # RQ2: add equal-mean boundary compositions; H1/R0 above is the midpoint.
    for seed in seeds:
        for workload in workloads:
            for load_name, rho in loads.items():
                for team in ("H0", "H2"):
                    design.append(
                        RunConfig(
                            seed=seed,
                            strategy="CF_FIT",
                            workload=workload,
                            load_name=load_name,
                            rho=float(rho),
                            team=team,
                            resource_regime="R0",
                            **shared,
                        )
                    )
    return sorted(design, key=lambda item: item.run_id)


def source_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted((ROOT / "Code" / "conveyorflow_v2").glob("*.py")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def write_events(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Level 1 keeps event logs compact while avoiding compression becoming the
    # dominant cost of a simulation-only pilot.
    with gzip.open(path, "wt", encoding="utf-8", newline="\n", compresslevel=1) as handle:
        for event in events:
            handle.write(json.dumps(event, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def execute_one(payload: tuple[dict, str, str]) -> dict:
    config_dict, root_text, event_dir_text = payload
    config = RunConfig(**config_dict)
    result = run_simulation(config, Path(root_text))
    write_events(Path(event_dir_text) / f"{result.run_id}.jsonl.gz", result.events)
    return result.metrics


def read_partial(path: Path) -> dict[str, dict]:
    completed: dict[str, dict] = {}
    if not path.exists():
        return completed
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                completed[record["run_id"]] = record
    return completed


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the registered ConveyorFlow v2 pilot.")
    parser.add_argument("--smoke", action="store_true", help="Run the reduced pre-pilot matrix.")
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()

    settings = json.loads((ROOT / "config" / "pilot.json").read_text(encoding="utf-8"))
    design = build_design(settings, args.smoke)
    output = ROOT / "results" / ("smoke" if args.smoke else "pilot")
    event_dir = output / "events"
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "design.csv", [{"run_id": item.run_id, **asdict(item)} for item in design])
    metadata = {
        "kind": "SMOKE" if args.smoke else "PILOT",
        "not_main_experiment": True,
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
    print(f"{metadata['kind']}: {len(design)} total, {len(completed)} resumed, {len(pending)} pending", flush=True)
    started = time.time()
    if pending:
        with partial.open("a", encoding="utf-8", newline="\n") as handle:
            with ProcessPoolExecutor(max_workers=max(1, args.workers)) as executor:
                futures = {
                    executor.submit(
                        execute_one,
                        (asdict(item), str(ROOT), str(event_dir)),
                    ): item.run_id
                    for item in pending
                }
                for index, future in enumerate(as_completed(futures), start=1):
                    run_id = futures[future]
                    try:
                        row = future.result()
                    except Exception as exc:
                        print(f"FAILED {run_id}: {exc!r}", flush=True)
                        raise
                    completed[run_id] = row
                    handle.write(json.dumps(row, sort_keys=True, allow_nan=True) + "\n")
                    handle.flush()
                    if index == 1 or index % 50 == 0 or index == len(pending):
                        elapsed = time.time() - started
                        print(f"completed {index}/{len(pending)} pending runs in {elapsed:.1f}s", flush=True)

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
