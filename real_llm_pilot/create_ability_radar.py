from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "figures"


def latest(root: Path, required: str) -> Path:
    return sorted((path for path in root.iterdir() if path.is_dir() and (path / required).exists()), reverse=True)[0]


def main() -> int:
    cross_run = latest(HERE / "heterogeneity_screen_output", "screen_final_summary.json")
    tencent_run = latest(HERE / "tencent_screen_output", "screen_summary.json")
    cross = {row["model_id"]: row for row in json.loads((cross_run / "screen_final_summary.json").read_text(encoding="utf-8"))["models"]}
    tencent = {row["model_id"]: row for row in json.loads((tencent_run / "screen_summary.json").read_text(encoding="utf-8"))["models"]}
    rows = {
        "Tencent HY3": tencent["tencent-hy3"],
        "GPT-5 mini": cross["gpt-5-mini"],
        "GLM 5.3 Flash": cross["glm-5.3-flash"],
    }
    axes = [("ml_build", "D1"), ("ml_build", "D2"), ("ml_build", "D3"), ("fix_bug", "D3"), ("fix_bug", "D2"), ("fix_bug", "D1")]
    labels = ["ML D1", "ML D2", "ML D3", "Fix D3", "Fix D2", "Fix D1"]
    angles = np.linspace(0, 2 * math.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]
    colors = {"Tencent HY3": "#E45756", "GPT-5 mini": "#4C78A8", "GLM 5.3 Flash": "#54A24B"}

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(10.5, 9.0), subplot_kw={"polar": True})
    fig.patch.set_facecolor("#F8FAFC")
    ax.set_facecolor("#FFFFFF")
    for label, row in rows.items():
        values = [row["cells"][family][difficulty]["pass_rate"] for family, difficulty in axes]
        values += values[:1]
        ax.plot(angles, values, color=colors[label], linewidth=2.6, marker="o", markersize=6, label=label)
        ax.fill(angles, values, color=colors[label], alpha=0.10)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11, fontweight="semibold", color="#243447")
    ax.tick_params(axis="x", pad=10)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["20%", "40%", "60%", "80%", "100%"], fontsize=9, color="#64748B")
    ax.grid(color="#CBD5E1", linewidth=0.8, alpha=0.8)
    ax.spines["polar"].set_color("#94A3B8")
    ax.set_title("Workload-Specific Ability Calibration\nDescriptive pass rates (5 probes per difficulty cell)", pad=30, fontsize=16, fontweight="bold", color="#0F172A")
    ax.set_position([0.14, 0.20, 0.72, 0.64])
    legend = ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.23), ncol=3, frameon=False, fontsize=10)
    for text in legend.get_texts():
        text.set_color("#243447")
    fig.text(0.5, 0.055, "Radar area is descriptive only; Ability Rank uses predeclared Wilson lower-bound gates.", ha="center", fontsize=9, color="#64748B")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "fig_ability_profile_radar.png", dpi=300, facecolor=fig.get_facecolor())
    fig.savefig(OUTPUT / "fig_ability_profile_radar.pdf", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(OUTPUT / "fig_ability_profile_radar.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
