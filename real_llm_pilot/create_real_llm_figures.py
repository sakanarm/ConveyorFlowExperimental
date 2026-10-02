"""Create descriptive publication figures from validated Real-LLM summaries.

Radar charts are visualization aids only. Formal claims remain metric-level.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
MAIN = HERE / "main_mfec_aggregated" / "real_llm_descriptive.csv"
EXTENSION = HERE / "extension_mfec_aggregated" / "extension_descriptive.csv"
OUTPUT = HERE / "figures"

AXES = [
    ("completion_rate", "Completion", True),
    ("cost_per_verified_task", "Cost efficiency", False),
    ("run_wall_time_seconds", "Speed", False),
    ("verified_throughput_per_second", "Throughput", True),
    ("resource_utilization", "Utilization", True),
]


def load_means(path: Path, key_field: str) -> dict[str, dict[str, float]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result: dict[str, dict[str, float]] = {}
    for row in rows:
        result.setdefault(row[key_field], {})[row["metric"]] = float(row["mean"])
    return result


def normalize(data: dict[str, dict[str, float]], order: list[str]) -> dict[str, list[float]]:
    normalized = {name: [] for name in order}
    for metric, _label, higher_is_better in AXES:
        values = [data[name][metric] for name in order]
        low, high = min(values), max(values)
        for name, value in zip(order, values, strict=True):
            if math.isclose(low, high):
                score = 0.5
            else:
                score = (value - low) / (high - low)
            normalized[name].append(score if higher_is_better else 1 - score)
    return normalized


def radar(
    data: dict[str, dict[str, float]],
    *,
    order: list[str],
    labels: dict[str, str],
    colors: dict[str, str],
    title: str,
    subtitle: str,
    stem: str,
    mark_timing_exploratory: bool,
) -> None:
    scores = normalize(data, order)
    count = len(AXES)
    angles = np.linspace(0, 2 * np.pi, count, endpoint=False).tolist()
    closed_angles = angles + angles[:1]
    fig, axis = plt.subplots(figsize=(10.0, 8.0), subplot_kw={"polar": True})
    fig.patch.set_facecolor("white")
    axis.set_facecolor("#FAFBFC")
    for name in order:
        values = scores[name] + scores[name][:1]
        axis.plot(closed_angles, values, color=colors[name], linewidth=2.4, marker="o", markersize=5, label=labels[name])
        axis.fill(closed_angles, values, color=colors[name], alpha=0.07)
    axis.set_xticks(angles)
    axis_labels = [
        f"{label}*" if mark_timing_exploratory and metric in {
            "run_wall_time_seconds", "verified_throughput_per_second", "resource_utilization"
        } else label
        for metric, label, _direction in AXES
    ]
    axis.set_xticklabels(axis_labels, fontsize=10.5, fontweight="semibold")
    axis.tick_params(axis="x", pad=12)
    for tick_label in axis.get_xticklabels():
        tick_label.set_zorder(10)
        tick_label.set_bbox({"facecolor": "white", "edgecolor": "none", "alpha": 0.86, "pad": 1.2})
    axis.set_ylim(0, 1)
    axis.set_yticks([0.25, 0.5, 0.75, 1.0])
    axis.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], fontsize=8, color="#667085")
    axis.grid(color="#CAD3DD", linewidth=0.7)
    axis.spines["polar"].set_color("#98A6B5")
    title_size = 14.5 if "\n" in title else 16
    fig.suptitle(title, fontsize=title_size, fontweight="bold", color="#15324C", y=0.94, linespacing=1.0)
    fig.text(0.5, 0.84, subtitle, ha="center", fontsize=10.5, color="#52616D")
    axis.legend(loc="lower center", bbox_to_anchor=(0.5, -0.30), ncol=2, frameon=False, fontsize=9.5)
    footnote = "Per-axis min-max normalization; higher is preferable."
    if mark_timing_exploratory:
        footnote += " *Cross-window wall-clock axes are exploratory; timing-valid n differs by condition."
    fig.text(
        0.5,
        0.025,
        footnote,
        ha="center",
        fontsize=8.3,
        color="#52616D",
    )
    axis.set_position([0.22, 0.28, 0.50, 0.50])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / f"{stem}.png", dpi=300, facecolor="white")
    fig.savefig(OUTPUT / f"{stem}.pdf", facecolor="white")
    plt.close(fig)


def main() -> int:
    main_data = load_means(MAIN, "policy")
    main_order = ["CF_FIT", "S3", "CENTRAL_FIT"]
    radar(
        main_data,
        order=main_order,
        labels={"CF_FIT": "CF-Fit", "S3": "Static round robin", "CENTRAL_FIT": "Central-Fit"},
        colors={"CF_FIT": "#0D6F78", "S3": "#D77A36", "CENTRAL_FIT": "#6B5CA5"},
        title="Real-LLM Allocation Trade-offs",
        subtitle="Three frozen allocation policies across ten paired seeds",
        stem="fig_real_llm_main_radar",
        mark_timing_exploratory=False,
    )

    extension_data = load_means(EXTENSION, "condition_id")
    extension_order = ["HET_FULL", "HET_NO_STANDDOWN", "HOM_GLM_GENERALIST", "HOM_GPT_PROFILE"]
    radar(
        extension_data,
        order=extension_order,
        labels={
            "HET_FULL": "Heterogeneous full CF-Fit",
            "HET_NO_STANDDOWN": "Heterogeneous without stand-down",
            "HOM_GLM_GENERALIST": "Homogeneous GLM",
            "HOM_GPT_PROFILE": "Homogeneous GPT",
        },
        colors={
            "HET_FULL": "#0D6F78",
            "HET_NO_STANDDOWN": "#D77A36",
            "HOM_GLM_GENERALIST": "#527A57",
            "HOM_GPT_PROFILE": "#6B5CA5",
        },
        title="Real-LLM Extension Sensitivity",
        subtitle="Stand-down ablation and homogeneous boundary conditions",
        stem="fig_real_llm_extension_radar",
        mark_timing_exploratory=True,
    )
    print(OUTPUT / "fig_real_llm_main_radar.png")
    print(OUTPUT / "fig_real_llm_extension_radar.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
