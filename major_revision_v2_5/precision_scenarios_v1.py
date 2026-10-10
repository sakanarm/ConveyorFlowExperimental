"""Descriptive cluster-level precision scenarios, not a power guarantee.

Repeated calls and cases from a source repository are not independent units.
This script uses the v2.4 paired pilot only to expose how sensitive a planned
confidence-interval width is to assumed between-repository dispersion.
"""

from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path
import statistics


HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "major_revision_v2_4/results/main_resume_v3/analysis.json"
OUT = HERE / "results/precision_scenarios_v1.json"
SIZES = (4, 8, 12, 20, 32, 64)
# Two-sided 95% Student-t critical values, df = n - 1.
T_CRITICAL = (3.182446, 2.364624, 2.200985, 2.093024, 2.039513, 1.998341)
ASSUMED_SD = (0.5, 1.0)
TARGET_HALF_WIDTH = 0.25  # jobs/hour; planning illustration, not investigator sign-off


def main() -> None:
    analysis = json.loads(PILOT.read_text(encoding="utf-8"))
    by_repo: dict[str, list[float]] = defaultdict(list)
    for block in analysis["blocks"]:
        arms = block["arms"]
        cf = arms["CF_FIT"]["metrics"]["throughput_verified_jobs_per_hour"]
        central = arms["CENTRAL_RULE_MATCHED"]["metrics"]["throughput_verified_jobs_per_hour"]
        by_repo[block["repository_project"]].append(cf - central)
    means = {repo: statistics.mean(diffs) for repo, diffs in sorted(by_repo.items())}
    pilot_sd = statistics.stdev(means.values())
    scenarios = []
    for sd in (pilot_sd, *ASSUMED_SD):
        for n, tcrit in zip(SIZES, T_CRITICAL):
            half_width = tcrit * sd / math.sqrt(n)
            scenarios.append({
                "independent_repository_clusters": n,
                "assumed_between_repository_sd_jobs_per_hour": sd,
                "approximate_95pct_t_interval_half_width_jobs_per_hour": half_width,
                "meets_illustrative_half_width_0_25": half_width <= TARGET_HALF_WIDTH,
            })
    result = {
        "status": "scenario_grid_not_sample_size_commitment",
        "pilot_complete_paired_blocks": len(analysis["blocks"]),
        "pilot_independent_repository_clusters": len(means),
        "pilot_repository_mean_cf_minus_central_jobs_per_hour": means,
        "pilot_between_repository_sd_jobs_per_hour": pilot_sd,
        "planning_target_half_width_jobs_per_hour": TARGET_HALF_WIDTH,
        "target_is_illustrative_not_advisor_signed_off": True,
        "assumed_sd_scenarios_jobs_per_hour": list(ASSUMED_SD),
        "unit_of_independence": "source repository (ML corpus clustering is separate and unresolved)",
        "formula": "t_{0.975,n-1} * assumed_between_repository_sd / sqrt(n)",
        "limitations": [
            "Only four pilot repositories; their observed SD is unstable and likely optimistic.",
            "This grid does not model within-repository case variation or two reused ML corpora.",
            "No equivalence, superiority, or power claim follows from reaching a row of this grid.",
            "The planning target and final hierarchical analysis need approval before paid extension.",
        ],
        "scenarios": scenarios,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        if json.loads(OUT.read_text(encoding="utf-8")) != result:
            raise ValueError("Scenario output drift; preserve original")
    else:
        with OUT.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps({
        "status": result["status"], "repository_clusters": len(means),
        "pilot_sd": pilot_sd,
        "half_width_if_sd_0_5_n_20": next(row[
            "approximate_95pct_t_interval_half_width_jobs_per_hour"] for row in scenarios
            if row["assumed_between_repository_sd_jobs_per_hour"] == 0.5 and
            row["independent_repository_clusters"] == 20),
        "half_width_if_sd_1_0_n_64": next(row[
            "approximate_95pct_t_interval_half_width_jobs_per_hour"] for row in scenarios
            if row["assumed_between_repository_sd_jobs_per_hour"] == 1.0 and
            row["independent_repository_clusters"] == 64),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
