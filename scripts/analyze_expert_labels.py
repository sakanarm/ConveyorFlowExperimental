from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def quadratic_weighted_kappa(left: list[int], right: list[int]) -> float:
    categories = (1, 2, 3)
    observed = Counter(zip(left, right))
    left_counts, right_counts = Counter(left), Counter(right)
    total = len(left)
    weighted_observed = 0.0
    weighted_expected = 0.0
    for a in categories:
        for b in categories:
            weight = ((a - b) / 2) ** 2
            weighted_observed += weight * observed[(a, b)] / total
            weighted_expected += weight * (left_counts[a] * right_counts[b]) / (total * total)
    return 1.0 - weighted_observed / weighted_expected if weighted_expected else 1.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", default=str(ROOT / "expert_labels" / "expert_labels_merged.csv")
    )
    args = parser.parse_args()
    path = Path(args.input)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    labelled = [
        row
        for row in rows
        if all(row[f"rater{i}_difficulty"].strip() for i in (1, 2, 3))
    ]
    if len(labelled) != len(rows):
        raise SystemExit(f"incomplete labels: {len(labelled)}/{len(rows)} items")
    ratings = {
        i: [int(row[f"rater{i}_difficulty"]) for row in labelled]
        for i in (1, 2, 3)
    }
    if any(value not in {1, 2, 3} for values in ratings.values() for value in values):
        raise SystemExit("difficulty values must be 1, 2, or 3")
    pairwise = {}
    for a, b in ((1, 2), (1, 3), (2, 3)):
        left, right = ratings[a], ratings[b]
        pairwise[f"rater{a}_rater{b}"] = {
            "exact_agreement": sum(x == y for x, y in zip(left, right)) / len(left),
            "adjacent_agreement": sum(abs(x - y) <= 1 for x, y in zip(left, right)) / len(left),
            "quadratic_weighted_kappa": quadratic_weighted_kappa(left, right),
        }
    kappas = [value["quadratic_weighted_kappa"] for value in pairwise.values()]
    by_workload = {}
    for workload in sorted({row["workload"] for row in labelled}):
        selected = [index for index, row in enumerate(labelled) if row["workload"] == workload]
        workload_pairs = {}
        for a, b in ((1, 2), (1, 3), (2, 3)):
            left = [ratings[a][index] for index in selected]
            right = [ratings[b][index] for index in selected]
            workload_pairs[f"rater{a}_rater{b}"] = {
                "exact_agreement": sum(x == y for x, y in zip(left, right)) / len(left),
                "quadratic_weighted_kappa": quadratic_weighted_kappa(left, right),
            }
        by_workload[workload] = workload_pairs
    distribution = Counter(
        int(row["adjudicated_difficulty"])
        for row in labelled
        if row["adjudicated_difficulty"].strip()
    )
    report = {
        "items": len(rows),
        "rater_type": "same-model_role-conditioned_LLM_passes",
        "pairwise_agreement": pairwise,
        "pairwise_agreement_by_workload": by_workload,
        "rater_difficulty_distribution": {
            f"rater{i}": dict(sorted(Counter(ratings[i]).items())) for i in (1, 2, 3)
        },
        "minimum_pairwise_quadratic_weighted_kappa": min(kappas),
        "agreement_gate": "PASS" if min(kappas) >= 0.70 else "REVIEW" if min(kappas) >= 0.60 else "FAIL",
        "items_requiring_adjudication": sum(
            row.get("adjudication_required", "") == "1" for row in labelled
        ),
        "adjudicated_items": sum(distribution.values()),
        "adjudicated_distribution": dict(sorted(distribution.items())),
        "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    output = path.with_name("expert_label_agreement.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
