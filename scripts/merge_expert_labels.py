from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IDENTITY_FIELDS = (
    "item_id",
    "workload",
    "variant",
    "stage",
    "skill",
    "dependency_count",
    "base_effort_reference",
    "corpus_context",
    "variant_context",
    "task_description",
)


def read_unique(path: Path) -> dict[str, dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    indexed = {row["item_id"]: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f"duplicate item_id in {path}")
    return indexed


SCORE_FIELDS = (
    "ambiguity_score",
    "scope_score",
    "dependency_score",
    "reasoning_score",
    "verification_score",
)


def validate_label(row: dict, path: Path) -> None:
    for field in SCORE_FIELDS:
        if row[field].strip() not in {"0", "1", "2"}:
            raise ValueError(f"invalid {field} for {row['item_id']} in {path}")
    total = sum(int(row[field]) for field in SCORE_FIELDS)
    expected = 1 if total <= 3 else 2 if total <= 6 else 3
    if row["difficulty"].strip() not in {"1", "2", "3"}:
        raise ValueError(f"invalid difficulty for {row['item_id']} in {path}")
    if int(row["difficulty"]) != expected:
        raise ValueError(
            f"difficulty does not match rubric total for {row['item_id']} in {path}: "
            f"total={total}, expected={expected}"
        )
    if row["failure_impact"].strip() not in {"1", "2", "3"}:
        raise ValueError(f"invalid failure impact for {row['item_id']} in {path}")
    if row["confidence"].strip() not in {"1", "2", "3", "4", "5"}:
        raise ValueError(f"invalid confidence for {row['item_id']} in {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rater1", default=str(ROOT / "expert_labels" / "rater1_blinded_packet.csv"))
    parser.add_argument("--rater2", default=str(ROOT / "expert_labels" / "rater2_blinded_packet.csv"))
    parser.add_argument("--rater3", default=str(ROOT / "expert_labels" / "rater3_blinded_packet.csv"))
    parser.add_argument("--output", default=str(ROOT / "expert_labels" / "expert_labels_merged.csv"))
    args = parser.parse_args()
    p1, p2, p3 = Path(args.rater1), Path(args.rater2), Path(args.rater3)
    r1, r2, r3 = read_unique(p1), read_unique(p2), read_unique(p3)
    if set(r1) != set(r2) or set(r1) != set(r3):
        raise ValueError("rater packets do not contain the same item IDs")
    rows = []
    for item_id in sorted(r1):
        left, right, third = r1[item_id], r2[item_id], r3[item_id]
        validate_label(left, p1)
        validate_label(right, p2)
        validate_label(third, p3)
        if any(
            left[field] != right[field] or left[field] != third[field]
            for field in IDENTITY_FIELDS
        ):
            raise ValueError(f"item metadata mismatch for {item_id}")
        votes = [left["difficulty"], right["difficulty"], third["difficulty"]]
        consensus = max(set(votes), key=votes.count) if len(set(votes)) < 3 else ""
        rows.append(
            {
                **{field: left[field] for field in IDENTITY_FIELDS},
                "rater1_difficulty": left["difficulty"],
                "rater1_failure_impact": left["failure_impact"],
                "rater1_confidence": left["confidence"],
                "rater1_reason": left["reason"],
                "rater2_difficulty": right["difficulty"],
                "rater2_failure_impact": right["failure_impact"],
                "rater2_confidence": right["confidence"],
                "rater2_reason": right["reason"],
                "rater3_difficulty": third["difficulty"],
                "rater3_failure_impact": third["failure_impact"],
                "rater3_confidence": third["confidence"],
                "rater3_reason": third["reason"],
                "consensus_difficulty": consensus,
                "adjudication_required": "0" if len(set(votes)) == 1 else "1",
                "adjudicated_difficulty": "",
                "adjudication_reason": "",
            }
        )
    output = Path(args.output)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"merged {len(rows)} blinded role-conditioned LLM labels to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
