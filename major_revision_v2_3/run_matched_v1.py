"""Execute frozen v2.3 paired architecture simulation and parity audits."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Code"))
sys.path.insert(0, str(HERE))

from conveyorflow_v2.workloads import llm_difficulty_path  # noqa: E402
from matched_architecture import (  # noqa: E402
    ArchitectureConfig,
    matched_event_stream,
    run_architecture,
)


CONFIG = HERE / "config_matched_v1.json"
RESULTS = HERE / "results" / "matched_v1"
IDENTITY_KEYS = {"run_id", "strategy", "event_hash", "config_hash"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def design(settings: dict) -> list[dict]:
    cells = []
    for seed in range(settings["seed_start"], settings["seed_start"] + settings["seeds"]):
        for workload in settings["workloads"]:
            for load_name, rho in settings["loads"].items():
                for regime in settings["resource_regimes"]:
                    for environment in settings["environments"]:
                        cells.append(
                            {
                                "seed": seed,
                                "workload": workload,
                                "load_name": load_name,
                                "rho": rho,
                                "resource_regime": regime,
                                "environment": environment,
                            }
                        )
    if len(cells) != settings["expected_pairs"]:
        raise AssertionError(f"design has {len(cells)} rather than expected pairs")
    return cells


def make_config(cell: dict, settings: dict, strategy: str) -> ArchitectureConfig:
    return ArchitectureConfig(
        seed=cell["seed"],
        strategy=strategy,
        workload=cell["workload"],
        load_name=cell["load_name"],
        rho=cell["rho"],
        team=settings["team"],
        resource_regime=cell["resource_regime"],
        n_jobs=settings["n_jobs"],
        k_scan=settings["k_scan"],
        max_attempts=settings["max_attempts"],
        w1=settings["w1"],
        w2=settings["w2"],
        w3=settings["w3"],
        requeue_limit=settings["requeue_limit"],
        drain_ticks=settings["drain_ticks"],
        fallback=settings["fallback"],
        difficulty_source=settings["difficulty_source"],
        environment=cell["environment"],
        outage_start_fraction=settings["outage_start_fraction"],
        outage_duration_fraction=settings["outage_duration_fraction"],
    )


def execute_cell(cell: dict, settings: dict) -> tuple[list[dict], dict]:
    results = {
        strategy: run_architecture(make_config(cell, settings, strategy), ROOT)
        for strategy in settings["strategies"]
    }
    local = results["CF_FIT"]
    central = results["CENTRAL_MATCHED"]
    stream_equal = matched_event_stream(local.events) == matched_event_stream(central.events)
    metrics_equal = (
        {key: value for key, value in local.metrics.items() if key not in IDENTITY_KEYS}
        == {key: value for key, value in central.metrics.items() if key not in IDENTITY_KEYS}
    )
    if cell["environment"] in {"E0", "E2_BELT"} and not (stream_equal and metrics_equal):
        raise AssertionError(f"matched parity failed for {cell}")
    pair_id = (
        f"{cell['environment']}__{cell['workload']}__{cell['load_name']}__"
        f"{cell['resource_regime']}__s{cell['seed']}"
    )
    metrics = []
    for strategy, result in results.items():
        row = dict(result.metrics)
        row.update({"pair_id": pair_id, "environment": cell["environment"]})
        metrics.append(row)
    audit = {
        "pair_id": pair_id,
        "environment": cell["environment"],
        "stream_equal": stream_equal,
        "metrics_equal": metrics_equal,
        "local_event_hash": local.event_hash,
        "central_event_hash": central.event_hash,
        "local_events": len(local.events),
        "central_events": len(central.events),
        "local_coordinator_outage_events": sum(
            event["event"] == "coordinator_unavailable" for event in local.events
        ),
        "central_coordinator_outage_events": sum(
            event["event"] == "coordinator_unavailable" for event in central.events
        ),
    }
    return metrics, audit


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("cannot write empty result set")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true", help="run 3 pairs separately; not research results")
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        raise ValueError("workers must be between 1 and 8")
    settings = json.loads(CONFIG.read_text(encoding="utf-8"))
    cells = design(settings)
    if args.smoke:
        cells = [
            next(cell for cell in cells if cell["environment"] == environment)
            for environment in settings["environments"]
        ]
    output = RESULTS / "smoke" if args.smoke else RESULTS / "main"
    if output.exists():
        raise FileExistsError(f"output exists; refusing to overwrite: {output}")
    output.mkdir(parents=True)
    started = time.monotonic()
    metrics_rows: list[dict] = []
    audit_rows: list[dict] = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(execute_cell, cell, settings): cell for cell in cells}
        for index, future in enumerate(as_completed(futures), start=1):
            metrics, audit = future.result()
            metrics_rows.extend(metrics)
            audit_rows.append(audit)
            if index % 50 == 0 or index == len(cells):
                print(f"completed_pairs={index}/{len(cells)}", flush=True)
    metrics_rows.sort(key=lambda row: (row["pair_id"], row["strategy"]))
    audit_rows.sort(key=lambda row: row["pair_id"])
    write_csv(output / "metrics.csv", metrics_rows)
    write_csv(output / "pair_audit.csv", audit_rows)
    label_path = llm_difficulty_path(ROOT, settings["difficulty_source"])
    manifest = {
        "status": "smoke_not_research_results" if args.smoke else "completed_simulation",
        "research_results": not args.smoke,
        "pairs": len(audit_rows),
        "runs": len(metrics_rows),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "parity_required_pairs": sum(row["environment"] in {"E0", "E2_BELT"} for row in audit_rows),
        "parity_failed_pairs": sum(
            row["environment"] in {"E0", "E2_BELT"}
            and not (row["stream_equal"] and row["metrics_equal"])
            for row in audit_rows
        ),
        "sha256": {
            "config": sha256(CONFIG),
            "runner": sha256(Path(__file__)),
            "matched_engine": sha256(HERE / "matched_architecture.py"),
            "original_simulator": sha256(ROOT / "Code" / "conveyorflow_v2" / "simulator.py"),
            "difficulty_labels": sha256(label_path),
            "metrics": sha256(output / "metrics.csv"),
            "pair_audit": sha256(output / "pair_audit.csv"),
        },
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
