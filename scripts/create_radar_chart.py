"""Create the descriptive RQ1 trade-off radar chart used in both documents."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "v2" / "results" / "main" / "descriptive_summary.csv"
OUTPUT = ROOT / "v2" / "results" / "main" / "figures" / "fig6_rq1_tradeoff_radar.png"

METRICS = [
    ("cost_per_verified_task", "Cost / verified\ntask", False),
    ("verified_throughput", "Verified\nthroughput", True),
    ("p95_terminal_flow_time", "P95 terminal\ntime", False),
    ("task_completion_rate", "Completion", True),
    ("dead_letter_rate", "Low dead-letter", False),
    ("unsettled_rate", "Low unsettled", False),
]
POLICIES = ["CF_FIT", "CENTRAL_FIT", "S1", "S2", "S3"]
LABELS = {
    "CF_FIT": "CF-Fit",
    "CENTRAL_FIT": "Central-Fit",
    "S1": "S1 fixed skill",
    "S2": "S2 fixed difficulty",
    "S3": "S3 round robin",
}
COLORS = {
    "CF_FIT": "#007C91",
    "CENTRAL_FIT": "#6F4E9C",
    "S1": "#7A7A7A",
    "S2": "#D97904",
    "S3": "#3E6FB0",
}


def normalize_panel(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.set_index("strategy").loc[POLICIES].copy()
    for column, _, higher_is_better in METRICS:
        values = result[column].astype(float)
        span = values.max() - values.min()
        if span == 0:
            result[column] = 0.5
        elif higher_is_better:
            result[column] = (values - values.min()) / span
        else:
            result[column] = (values.max() - values) / span
    return result


def main() -> None:
    data = pd.read_csv(SOURCE)
    data = data[data["family"].eq("RQ1")]
    angles = np.linspace(0, 2 * np.pi, len(METRICS), endpoint=False)
    closed_angles = np.r_[angles, angles[0]]

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titleweight": "bold",
    })
    figure, axes = plt.subplots(
        1, 2, figsize=(10.8, 6.2), subplot_kw={"projection": "polar"}, constrained_layout=False
    )
    figure.patch.set_facecolor("white")

    for axis, regime in zip(axes, ("R0", "R1")):
        panel = normalize_panel(data[data["resource_regime"].eq(regime)])
        axis.set_theta_offset(np.pi / 2)
        axis.set_theta_direction(-1)
        axis.set_xticks(angles)
        axis.set_xticklabels([label for _, label, _ in METRICS], fontsize=8.5, color="#263238")
        axis.tick_params(axis="x", pad=10)
        axis.set_ylim(0, 1)
        axis.set_yticks([0.25, 0.50, 0.75, 1.00])
        axis.set_yticklabels([".25", ".50", ".75", "1.00"], fontsize=7, color="#718096")
        axis.set_rlabel_position(18)
        axis.grid(color="#C9D2D9", linewidth=0.7, alpha=0.85)
        axis.spines["polar"].set_color("#9AA9B2")
        axis.set_title(
            f"{regime}: " + ("ability separated from resource cost" if regime == "R0" else "ability coupled to resource cost"),
            fontsize=11, color="#173F5F", pad=18,
        )

        for policy in POLICIES:
            values = np.array([panel.loc[policy, column] for column, _, _ in METRICS])
            closed_values = np.r_[values, values[0]]
            width = 2.8 if policy == "CF_FIT" else (2.1 if policy == "CENTRAL_FIT" else 1.35)
            alpha = 1.0 if policy in {"CF_FIT", "CENTRAL_FIT"} else 0.78
            axis.plot(
                closed_angles, closed_values, color=COLORS[policy], linewidth=width,
                marker="o", markersize=4 if policy == "CF_FIT" else 2.8,
                alpha=alpha, label=LABELS[policy], zorder=5 if policy == "CF_FIT" else 3,
            )
            if policy == "CF_FIT":
                axis.fill(closed_angles, closed_values, color=COLORS[policy], alpha=0.12, zorder=1)

    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(
        handles, labels, loc="lower center", ncol=5, frameon=False,
        bbox_to_anchor=(0.5, 0.035), fontsize=8.5, handlelength=2.4,
    )
    figure.suptitle(
        "RQ1 descriptive trade-off profiles (higher normalized desirability is better)",
        fontsize=14, fontweight="bold", color="#173F5F", y=0.985,
    )
    figure.text(
        0.5, 0.008,
        "Within-regime min-max normalization across the five policies; descriptive only, not a composite inferential score.",
        ha="center", va="bottom", fontsize=8, color="#4A5568",
    )
    figure.subplots_adjust(left=0.055, right=0.945, top=0.76, bottom=0.15, wspace=0.30)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT, dpi=320, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    print(OUTPUT)


if __name__ == "__main__":
    main()
