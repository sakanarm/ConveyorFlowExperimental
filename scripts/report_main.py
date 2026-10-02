from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_main import METRICS, ablation, read_metrics, scopes  # noqa: E402


OUTPUT = ROOT / "results" / "main"
FIGURES = OUTPUT / "figures"
LABELS = {
    "cost_per_verified_task": "Cost / verified task",
    "verified_throughput": "Verified throughput",
    "p95_terminal_flow_time": "P95 terminal time",
    "task_completion_rate": "Completion fraction",
    "dead_letter_rate": "Dead-letter fraction",
    "unsettled_rate": "Unsettled fraction",
    "productive_utilization": "Productive utilization",
}


def median(values: list[float]) -> float:
    return statistics.median(values)


def write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def read_effects() -> list[dict]:
    with (OUTPUT / "confirmatory_effects.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    numeric = {
        "n_seeds",
        "n_matched_cell_runs",
        "left_seed_median",
        "right_seed_median",
        "paired_seed_median_difference",
        "bootstrap_ci_low",
        "bootstrap_ci_high",
        "wilcoxon_statistic",
        "p_value",
        "rank_biserial",
        "p_holm",
    }
    for row in rows:
        for key in numeric:
            if row.get(key, "") != "":
                row[key] = float(row[key])
    return rows


def group_medians(rows: list[dict], *, family: str, keys: tuple[str, ...]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)
    output: list[dict] = []
    for key_values, group in sorted(grouped.items(), key=lambda item: tuple(map(str, item[0]))):
        result = {"family": family, **dict(zip(keys, key_values)), "runs": len(group)}
        for metric in METRICS:
            result[metric] = median([float(row[metric]) for row in group])
        output.append(result)
    return output


def descriptive_summary(rows: list[dict]) -> list[dict]:
    output: list[dict] = []
    rq1 = [row for row in rows if "RQ1" in scopes(row)]
    output.extend(group_medians(rq1, family="RQ1", keys=("resource_regime", "strategy")))

    rq2 = [row for row in rows if "RQ2" in scopes(row) and row["strategy"] == "CF_FIT"]
    output.extend(group_medians(rq2, family="RQ2", keys=("resource_regime", "team")))

    rq3 = [row.copy() for row in rows if "RQ3" in scopes(row) and row["strategy"] == "CF_FIT"]
    for row in rq3:
        row["ablation"] = ablation(row)
    output.extend(group_medians(rq3, family="RQ3", keys=("resource_regime", "ablation")))

    e4 = [row for row in rows if "E4" in scopes(row) and row["strategy"] == "CF_FIT"]
    output.extend(
        group_medians(
            e4,
            family="E4",
            keys=("resource_regime", "difficulty_profile", "fallback"),
        )
    )
    return output


def effect_index(effects: list[dict]) -> dict[tuple[str, str, str, str], dict]:
    return {
        (row["family"], row["stratum"], row["contrast"], row["metric"]): row
        for row in effects
    }


def fmt(value: float, digits: int = 3) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.{digits}f}"


def pct_effect(row: dict) -> str:
    right = float(row["right_seed_median"])
    difference = float(row["paired_seed_median_difference"])
    if right == 0 or not math.isfinite(right):
        return fmt(difference)
    return f"{100.0 * difference / abs(right):+.1f}%"


def sig(row: dict) -> str:
    return "*" if float(row["p_holm"]) < 0.05 else ""


def build_results_markdown(
    rows: list[dict], effects: list[dict], integrity: dict, verification: dict
) -> str:
    idx = effect_index(effects)
    lines = [
        "# ConveyorFlow Main Results — Confirmatory Simulation",
        "",
        "## Integrity",
        "",
        f"- Completed runs: {integrity['observed_runs']:,}/{integrity['expected_runs']:,}",
        f"- Unique run IDs: {integrity['unique_run_ids']:,}; duplicates: {integrity['duplicate_run_ids']:,}",
        f"- Zero-success runs: {integrity['zero_success_runs']:,}",
        f"- Artifact verification: {verification['status'].upper()}; event hashes checked: {verification['event_hashes_checked']:,}",
        f"- Source hash match: {verification['source_hash_matches']}",
        "",
        "All confirmatory statements below are conditional on the frozen discrete-event simulation. "
        "They are not measurements of named commercial LLMs.",
        "",
        "## RQ1 — CF-Fit versus static and centralized allocation",
        "",
        "Percentages are paired median differences relative to the comparator median. "
        "Asterisks mark Holm-adjusted p<0.05. Negative cost and P95 time are favorable; "
        "positive throughput is favorable.",
        "",
        "| Resource | Comparator | Cost | Throughput | P95 time | Completion NI | Dead-letter NI | Unsettled NI |",
        "|---|---|---:|---:|---:|:---:|:---:|:---:|",
    ]
    for resource in ("R0", "R1"):
        for comparator in ("S1", "S2", "S3", "CENTRAL_FIT"):
            contrast = f"CF_FIT_minus_{comparator}"
            cost = idx[("RQ1", resource, contrast, "cost_per_verified_task")]
            throughput = idx[("RQ1", resource, contrast, "verified_throughput")]
            p95 = idx[("RQ1", resource, contrast, "p95_terminal_flow_time")]
            completion = idx[("RQ1", resource, contrast, "task_completion_rate")]
            dead = idx[("RQ1", resource, contrast, "dead_letter_rate")]
            unsettled = idx[("RQ1", resource, contrast, "unsettled_rate")]
            lines.append(
                f"| {resource} | {comparator} | {pct_effect(cost)}{sig(cost)} | "
                f"{pct_effect(throughput)}{sig(throughput)} | {pct_effect(p95)}{sig(p95)} | "
                f"{completion['noninferiority_pass']} | {dead['noninferiority_pass']} | "
                f"{unsettled['noninferiority_pass']} |"
            )

    lines.extend(
        [
            "",
            "## RQ2 — Capability heterogeneity under CF-Fit",
            "",
            "H0=(2,2,2,2), H1=(1,2,2,3), and H2=(1,1,3,3) hold team size and mean "
            "ability constant while increasing ability variance.",
            "",
            "| Resource | Contrast | Cost | Throughput | P95 time | Completion Δ |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for resource in ("R0", "R1"):
        for contrast in ("H1_minus_H0", "H2_minus_H0", "H2_minus_H1"):
            cost = idx[("RQ2", resource, contrast, "cost_per_verified_task")]
            throughput = idx[("RQ2", resource, contrast, "verified_throughput")]
            p95 = idx[("RQ2", resource, contrast, "p95_terminal_flow_time")]
            completion = idx[("RQ2", resource, contrast, "task_completion_rate")]
            lines.append(
                f"| {resource} | {contrast} | {pct_effect(cost)}{sig(cost)} | "
                f"{pct_effect(throughput)}{sig(throughput)} | {pct_effect(p95)}{sig(p95)} | "
                f"{fmt(float(completion['paired_seed_median_difference']))}{sig(completion)} |"
            )

    lines.extend(
        [
            "",
            "## RQ3 — Component ablations",
            "",
            "The direction is Full minus ablation. A small A3 effect means stand-down is a "
            "bounded refinement rather than the sole explanation for CF-Fit.",
            "",
            "| Resource | Removed component | Cost | Throughput | P95 time | Completion Δ |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for resource in ("R0", "R1"):
        for name, label in (
            ("A1", "Assessment"),
            ("A2", "Fit"),
            ("A3", "Stand-down"),
            ("A4", "Aging"),
        ):
            contrast = f"FULL_minus_{name}"
            cost = idx[("RQ3", resource, contrast, "cost_per_verified_task")]
            throughput = idx[("RQ3", resource, contrast, "verified_throughput")]
            p95 = idx[("RQ3", resource, contrast, "p95_terminal_flow_time")]
            completion = idx[("RQ3", resource, contrast, "task_completion_rate")]
            lines.append(
                f"| {resource} | {label} | {pct_effect(cost)}{sig(cost)} | "
                f"{pct_effect(throughput)}{sig(throughput)} | {pct_effect(p95)}{sig(p95)} | "
                f"{fmt(float(completion['paired_seed_median_difference']))}{sig(completion)} |"
            )

    lines.extend(
        [
            "",
            "## E4 — No-volunteer fallback",
            "",
            "F2 is the decentralized aging-and-relaxation default. F3 is a hybrid reference "
            "because a central component forces rescue.",
            "",
            "| Resource | Contrast | Cost | Throughput | P95 time | Dead-letter Δ | Unsettled Δ |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for resource in ("R0", "R1"):
        for name in ("F0", "F1", "F3"):
            contrast = f"F2_minus_{name}"
            cost = idx[("E4", resource, contrast, "cost_per_verified_task")]
            throughput = idx[("E4", resource, contrast, "verified_throughput")]
            p95 = idx[("E4", resource, contrast, "p95_terminal_flow_time")]
            dead = idx[("E4", resource, contrast, "dead_letter_rate")]
            unsettled = idx[("E4", resource, contrast, "unsettled_rate")]
            lines.append(
                f"| {resource} | F2−{name} | {pct_effect(cost)}{sig(cost)} | "
                f"{pct_effect(throughput)}{sig(throughput)} | {pct_effect(p95)}{sig(p95)} | "
                f"{fmt(float(dead['paired_seed_median_difference']))}{sig(dead)} | "
                f"{fmt(float(unsettled['paired_seed_median_difference']))}{sig(unsettled)} |"
            )

    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "The manuscript must describe a multi-objective trade-off, not a universal winner. "
            "Non-inferiority decisions use frozen absolute margins of 0.03 for completion, "
            "dead-letter, and unsettled fractions. LLM-derived difficulty labels are design "
            "inputs with same-model procedural-stability evidence, not human expert ground truth.",
            "",
        ]
    )
    return "\n".join(lines)


def architecture_figure(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    colors = {"belt": "#DCEAF7", "agent": "#E7F2E4", "event": "#FFF0D5"}

    def box(x: float, y: float, w: float, h: float, text: str, color: str) -> None:
        patch = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.08",
            linewidth=1.2, edgecolor="#243447", facecolor=color,
        )
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9)

    box(0.2, 2.55, 1.6, 0.75, "Job DAGs\nML build / bug fix", colors["event"])
    box(2.35, 2.35, 3.2, 1.15, "READY conveyor belt\nordered frontier; K_scan=8", colors["belt"])
    for index, label in enumerate(("A1\nL1", "A2\nL2", "A3\nL2", "A4\nL3")):
        box(6.15 + (index % 2) * 1.35, 2.45 - (index // 2) * 1.35, 1.05, 0.75, label, colors["agent"])
    box(2.5, 0.35, 2.9, 0.85, "Atomic claim + event ledger\nexecute → verify → release DAG", colors["event"])
    for start, end in (
        ((1.8, 2.92), (2.35, 2.92)),
        ((5.55, 2.92), (6.15, 2.92)),
        ((5.55, 2.65), (7.5, 1.82)),
        ((6.15, 1.25), (5.4, 0.8)),
        ((2.5, 0.8), (1.0, 2.55)),
    ):
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="->", mutation_scale=12, lw=1.2, color="#425466"))
    ax.text(6.1, 3.63, "Local assess → volunteer → fit backoff\nOverqualified agents may stand down", fontsize=9, ha="left")
    ax.text(5.85, 0.45, "F2: age → relax threshold / stand-down\nthen bounded dead-letter", fontsize=8.5, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def forest_figure(effects: list[dict], family: str, metric: str, path: Path) -> None:
    selected = [
        row for row in effects
        if row["family"] == family and row["metric"] == metric
        and row["direction"] == "left-minus-right"
    ]
    selected.sort(key=lambda row: (row["stratum"], row["contrast"]))
    labels = [f"{row['stratum']}  {row['contrast'].replace('_minus_', ' − ')}" for row in selected]
    values = [float(row["paired_seed_median_difference"]) for row in selected]
    lows = [float(row["bootstrap_ci_low"]) for row in selected]
    highs = [float(row["bootstrap_ci_high"]) for row in selected]
    y = list(range(len(selected)))
    fig, ax = plt.subplots(figsize=(7.2, max(3.3, 0.38 * len(selected) + 1.2)))
    ax.errorbar(
        values,
        y,
        xerr=[[v - lo for v, lo in zip(values, lows)], [hi - v for v, hi in zip(values, highs)]],
        fmt="o",
        color="#155E75",
        ecolor="#5B8DA3",
        capsize=3,
    )
    ax.axvline(0, color="#6B7280", lw=1, ls="--")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel(f"Paired median difference: {LABELS[metric]} (left − right)")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    summary = json.loads((OUTPUT / "execution_summary.json").read_text(encoding="utf-8"))
    if summary.get("status") != "complete":
        raise SystemExit("refusing report generation: Main execution is not complete")
    rows = read_metrics(OUTPUT / "metrics.csv")
    effects = read_effects()
    integrity = json.loads((OUTPUT / "analysis_integrity.json").read_text(encoding="utf-8"))
    verification = json.loads((OUTPUT / "artifact_verification.json").read_text(encoding="utf-8"))
    if not integrity.get("pass") or verification.get("status") != "pass":
        raise SystemExit("refusing report generation: integrity or artifact verification failed")

    descriptive = descriptive_summary(rows)
    write_csv(OUTPUT / "descriptive_summary.csv", descriptive)
    markdown = build_results_markdown(rows, effects, integrity, verification)
    (OUTPUT / "MAIN_RESULTS_INTERPRETATION.md").write_text(markdown + "\n", encoding="utf-8")

    FIGURES.mkdir(parents=True, exist_ok=True)
    architecture_figure(FIGURES / "fig1_architecture.png")
    forest_figure(effects, "RQ1", "cost_per_verified_task", FIGURES / "fig2_rq1_cost.png")
    forest_figure(effects, "RQ2", "verified_throughput", FIGURES / "fig3_rq2_throughput.png")
    forest_figure(effects, "RQ3", "cost_per_verified_task", FIGURES / "fig4_rq3_cost.png")
    forest_figure(effects, "E4", "dead_letter_rate", FIGURES / "fig5_e4_deadletter.png")
    print(
        json.dumps(
            {
                "status": "complete",
                "descriptive_rows": len(descriptive),
                "effect_rows": len(effects),
                "figures": 5,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
