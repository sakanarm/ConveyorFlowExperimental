from __future__ import annotations

import argparse
import csv
import gzip
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "main"
EVENTS = RESULTS / "events"
FIGURES = RESULTS / "figures"

STRATEGY_ORDER = ["CF_FIT", "CENTRAL_FIT", "S1", "S2", "S3"]
DISPLAY = {
    "CF_FIT": "CF-Fit",
    "CENTRAL_FIT": "Central-Fit",
    "S1": "Static L3-only",
    "S2": "Static L1-only",
    "S3": "Static round-robin",
}
COLORS = {
    "CF_FIT": "#0072B2",
    "CENTRAL_FIT": "#D55E00",
    "S1": "#009E73",
    "S2": "#CC79A7",
    "S3": "#E69F00",
}


def aalen_johansen(times: np.ndarray, status: np.ndarray, grid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return verified/dead-letter cumulative incidence on a fixed grid.

    status: 0 = right censored, 1 = verified, 2 = dead letter.
    """
    order = np.argsort(times, kind="mergesort")
    times = times[order]
    status = status[order]
    unique_times, starts, counts = np.unique(times, return_index=True, return_counts=True)
    survival = 1.0
    cif_verified = 0.0
    cif_dead = 0.0
    verified_steps: list[float] = []
    dead_steps: list[float] = []
    n_total = len(times)
    for event_time, start, count in zip(unique_times, starts, counts):
        at_risk = n_total - int(start)
        group = status[start : start + count]
        d_verified = int(np.count_nonzero(group == 1))
        d_dead = int(np.count_nonzero(group == 2))
        if at_risk > 0:
            cif_verified += survival * d_verified / at_risk
            cif_dead += survival * d_dead / at_risk
            survival *= 1.0 - (d_verified + d_dead) / at_risk
        verified_steps.append(cif_verified)
        dead_steps.append(cif_dead)
    indexes = np.searchsorted(unique_times, grid, side="right") - 1
    verified = np.where(indexes >= 0, np.asarray(verified_steps)[np.maximum(indexes, 0)], 0.0)
    dead = np.where(indexes >= 0, np.asarray(dead_steps)[np.maximum(indexes, 0)], 0.0)
    return verified, dead


def analyze_event_file(payload: tuple) -> dict:
    (
        path_text,
        run_id,
        strategy,
        resource_regime,
        workload,
        load,
        expected_offered,
        expected_verified,
        expected_dead,
        expected_unsettled,
        grid_values,
    ) = payload
    path = Path(path_text)
    created: dict[str, int] = {}
    terminal: dict[str, tuple[int, int]] = {}
    horizon: int | None = None
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not any(
                marker in line
                for marker in ('"event":"run_start"', '"event":"task_created"', '"event":"task_terminal"')
            ):
                continue
            event = json.loads(line)
            kind = event["event"]
            if kind == "run_start":
                horizon = int(event["horizon"])
            elif kind == "task_created":
                created[event["task_id"]] = int(event["created_tick"])
            elif kind == "task_terminal":
                code = {"UNSETTLED": 0, "VERIFIED": 1, "DEAD_LETTER": 2}[event["outcome"]]
                terminal[event["task_id"]] = (int(event["flow_time"]), code)
    if horizon is None:
        raise ValueError(f"missing run_start in {path}")
    n_verified = sum(code == 1 for _, code in terminal.values())
    n_dead = sum(code == 2 for _, code in terminal.values())
    n_unsettled = sum(code == 0 for _, code in terminal.values()) + len(created) - len(terminal)
    observed = (len(created), n_verified, n_dead, n_unsettled)
    expected = (expected_offered, expected_verified, expected_dead, expected_unsettled)
    if observed != expected:
        raise ValueError(f"event/metric mismatch for {run_id}: observed={observed}, expected={expected}")
    times = np.empty(len(created), dtype=float)
    status = np.empty(len(created), dtype=np.int8)
    for index, (task_id, created_tick) in enumerate(created.items()):
        if task_id in terminal:
            times[index], status[index] = terminal[task_id]
        else:
            times[index] = max(0, horizon - created_tick)
            status[index] = 0
    grid = np.asarray(grid_values, dtype=float)
    verified_curve, dead_curve = aalen_johansen(times, status, grid)
    return {
        "run_id": run_id,
        "strategy": strategy,
        "resource_regime": resource_regime,
        "workload": workload,
        "load": load,
        "verified": verified_curve.tolist(),
        "dead": dead_curve.tolist(),
    }


def is_dominated(row: pd.Series, frame: pd.DataFrame, x: str, y: str, minimize_x: bool, maximize_y: bool) -> bool:
    for _, other in frame.iterrows():
        if other["strategy"] == row["strategy"]:
            continue
        x_no_worse = other[x] <= row[x] if minimize_x else other[x] >= row[x]
        y_no_worse = other[y] >= row[y] if maximize_y else other[y] <= row[y]
        x_strict = other[x] < row[x] if minimize_x else other[x] > row[x]
        y_strict = other[y] > row[y] if maximize_y else other[y] < row[y]
        if x_no_worse and y_no_worse and (x_strict or y_strict):
            return True
    return False


def create_pareto_outputs() -> dict:
    summary = pd.read_csv(RESULTS / "descriptive_summary.csv")
    rq1 = summary[summary["family"] == "RQ1"].copy()
    records: list[dict] = []
    objectives = [
        ("economic", "cost_per_verified_task", "verified_throughput", True, True),
        ("service_quality", "p95_terminal_flow_time", "task_completion_rate", True, True),
    ]
    for regime in ("R0", "R1"):
        frame = rq1[rq1["resource_regime"] == regime].copy()
        for objective, x, y, minimize_x, maximize_y in objectives:
            for _, row in frame.iterrows():
                records.append(
                    {
                        "resource_regime": regime,
                        "objective_space": objective,
                        "strategy": row["strategy"],
                        "x_metric": x,
                        "x_value": row[x],
                        "x_preference": "minimize" if minimize_x else "maximize",
                        "y_metric": y,
                        "y_value": row[y],
                        "y_preference": "maximize" if maximize_y else "minimize",
                        "pareto_nondominated": not is_dominated(row, frame, x, y, minimize_x, maximize_y),
                    }
                )
    pareto = pd.DataFrame.from_records(records)
    pareto.to_csv(RESULTS / "pareto_frontier_summary.csv", index=False, quoting=csv.QUOTE_MINIMAL)

    plt.rcParams.update({"font.size": 9, "font.family": "DejaVu Sans"})
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 8.0))
    label_offsets = {
        "CF_FIT": (7, -15),
        "CENTRAL_FIT": (-78, 8),
        "S1": (6, 6),
        "S2": (6, 6),
        "S3": (6, 6),
    }
    for row_index, regime in enumerate(("R0", "R1")):
        frame = rq1[rq1["resource_regime"] == regime].copy()
        for col_index, (objective, x, y, minimize_x, maximize_y) in enumerate(objectives):
            ax = axes[row_index, col_index]
            sub = pareto[(pareto["resource_regime"] == regime) & (pareto["objective_space"] == objective)]
            frontier = sub[sub["pareto_nondominated"]].sort_values("x_value")
            if len(frontier) > 1:
                ax.plot(frontier["x_value"], frontier["y_value"], color="#4D4D4D", lw=1.5, zorder=1)
            for strategy in STRATEGY_ORDER:
                point = frame[frame["strategy"] == strategy].iloc[0]
                nondominated = bool(sub[sub["strategy"] == strategy]["pareto_nondominated"].iloc[0])
                ax.scatter(
                    point[x],
                    point[y],
                    s=105 if nondominated else 70,
                    facecolor=COLORS[strategy] if nondominated else "white",
                    edgecolor=COLORS[strategy],
                    linewidth=1.8,
                    zorder=3,
                )
                offset = label_offsets[strategy]
                if objective == "service_quality" and strategy == "CENTRAL_FIT":
                    offset = (7, 8)
                ax.annotate(
                    DISPLAY[strategy],
                    (point[x], point[y]),
                    xytext=offset,
                    textcoords="offset points",
                    fontsize=8,
                )
            ax.grid(alpha=0.22)
            ax.set_title(f"{regime}: {'cost-throughput' if objective == 'economic' else 'time-completion'} frontier", fontweight="bold")
            if objective == "economic":
                ax.set_xlabel("Cost per verified task (lower is better)")
                ax.set_ylabel("Verified throughput (higher is better)")
            else:
                ax.set_xlabel("P95 terminal flow time (lower is better)")
                ax.set_ylabel("Task completion rate (higher is better)")
    fig.suptitle("RQ1 descriptive Pareto frontiers", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0.01, 1, 0.96], h_pad=2.2, w_pad=2.0)
    output = FIGURES / "fig7_rq1_pareto_frontiers.png"
    fig.savefig(output, dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return {
        "rows": len(pareto),
        "nondominated": {
            f"{regime}/{objective}": group["strategy"].tolist()
            for (regime, objective), group in pareto[pareto["pareto_nondominated"]].groupby(
                ["resource_regime", "objective_space"]
            )
        },
    }


def create_competing_risk_outputs(workers: int) -> dict:
    design = pd.read_csv(RESULTS / "design.csv")
    metrics = pd.read_csv(RESULTS / "metrics.csv")
    rq1_ids = set(design.loc[design["scopes"].fillna("").str.contains("RQ1"), "run_id"])
    rq1 = metrics[metrics["run_id"].isin(rq1_ids)].copy()
    if len(rq1) != 4500:
        raise ValueError(f"expected 4,500 RQ1 runs, found {len(rq1):,}")
    grid = np.arange(0, 1001, 10, dtype=float)
    payloads = []
    for row in rq1.itertuples(index=False):
        path = EVENTS / f"{row.run_id}.jsonl.gz"
        if not path.exists():
            raise FileNotFoundError(path)
        payloads.append(
            (
                str(path), row.run_id, row.strategy, row.resource_regime, row.workload, row.load,
                int(row.offered_tasks), int(row.verified_tasks), int(row.dead_letter_tasks), int(row.unsettled_tasks),
                grid.tolist(),
            )
        )
    results: list[dict] = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for index, item in enumerate(executor.map(analyze_event_file, payloads, chunksize=8), start=1):
            results.append(item)
            if index % 250 == 0 or index == len(payloads):
                print(f"competing-risk ledgers: {index}/{len(payloads)}", flush=True)

    checkpoints = [50, 100, 250, 500, 1000]
    summary_rows: list[dict] = []
    curves: dict[tuple[str, str, str], np.ndarray] = {}
    for regime in ("R0", "R1"):
        for strategy in STRATEGY_ORDER:
            group = [item for item in results if item["resource_regime"] == regime and item["strategy"] == strategy]
            if len(group) != 450:
                raise ValueError(f"expected 450 runs for {regime}/{strategy}, found {len(group)}")
            for cause in ("verified", "dead"):
                matrix = np.asarray([item[cause] for item in group], dtype=float)
                curves[(regime, strategy, cause)] = matrix
                for checkpoint in checkpoints:
                    column = int(np.where(grid == checkpoint)[0][0])
                    values = matrix[:, column]
                    summary_rows.append(
                        {
                            "resource_regime": regime,
                            "strategy": strategy,
                            "cause": "VERIFIED" if cause == "verified" else "DEAD_LETTER",
                            "time_tick": checkpoint,
                            "runs": len(group),
                            "median_cumulative_incidence": float(np.median(values)),
                            "p025_run_distribution": float(np.quantile(values, 0.025)),
                            "p975_run_distribution": float(np.quantile(values, 0.975)),
                        }
                    )
    summary = pd.DataFrame.from_records(summary_rows)
    summary.to_csv(RESULTS / "competing_risk_summary.csv", index=False)

    plt.rcParams.update({"font.size": 9, "font.family": "DejaVu Sans"})
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 7.8), sharex=True, sharey="row")
    for col_index, regime in enumerate(("R0", "R1")):
        for row_index, cause in enumerate(("verified", "dead")):
            ax = axes[row_index, col_index]
            for strategy in STRATEGY_ORDER:
                matrix = curves[(regime, strategy, cause)]
                median = np.median(matrix, axis=0)
                low = np.quantile(matrix, 0.025, axis=0)
                high = np.quantile(matrix, 0.975, axis=0)
                ax.plot(grid, median, color=COLORS[strategy], lw=1.8, label=DISPLAY[strategy])
                ax.fill_between(grid, low, high, color=COLORS[strategy], alpha=0.07, linewidth=0)
            ax.grid(alpha=0.2)
            ax.set_title(f"{regime}: {'verified' if cause == 'verified' else 'dead letter'}", fontweight="bold")
            if row_index == 1:
                ax.set_xlabel("Ticks since task creation")
            if col_index == 0:
                ax.set_ylabel("Cumulative incidence")
            ax.set_xlim(0, 1000)
            ax.set_ylim(0, 1.0)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 0.005))
    fig.suptitle("RQ1 task outcomes under competing risks", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0.065, 1, 0.96], h_pad=0.9, w_pad=1.5)
    output = FIGURES / "fig8_rq1_competing_risks.png"
    fig.savefig(output, dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return {"runs_checked": len(results), "summary_rows": len(summary), "grid_max": int(grid[-1])}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create secondary RQ1 Pareto and competing-risk analyses.")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    FIGURES.mkdir(parents=True, exist_ok=True)
    pareto = create_pareto_outputs()
    competing = create_competing_risk_outputs(max(1, args.workers))
    payload = {
        "status": "complete",
        "analysis_class": "secondary_exploratory",
        "pareto": pareto,
        "competing_risk": competing,
        "notes": [
            "Pareto frontiers are descriptive two-objective summaries and are not composite rankings.",
            "Competing-risk curves use task creation as time zero and VERIFIED/DEAD_LETTER as competing events.",
            "Unresolved tasks are right-censored at the run horizon; aggregation is across run-level curves.",
        ],
    }
    (RESULTS / "secondary_analysis_integrity.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
