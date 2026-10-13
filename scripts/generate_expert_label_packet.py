from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Code"))

from conveyorflow_v2.workloads import STAGES  # noqa: E402


def main() -> int:
    profiles = json.loads(
        (ROOT / "data" / "derived" / "corpus_profiles.json").read_text(encoding="utf-8")
    )
    variants = json.loads(
        (ROOT / "data" / "derived" / "annotation_variants.json").read_text(encoding="utf-8")
    )["variants"]
    output = ROOT / "expert_labels"
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for workload, stages in STAGES.items():
        profile = profiles[workload]
        context = json.dumps(
            {key: value for key, value in profile.items() if key != "difficulty_weights"},
            ensure_ascii=False,
            sort_keys=True,
        )
        for variant_record in variants[workload]:
            variant = int(variant_record["variant"])
            variant_context = json.dumps(variant_record, ensure_ascii=False, sort_keys=True)
            for stage in stages:
                rows.append(
                    {
                        "item_id": f"{workload}:V{variant:02d}:{stage.name}",
                        "workload": workload,
                        "variant": variant,
                        "stage": stage.name,
                        "skill": stage.skill,
                        "dependency_count": len(stage.deps),
                        "base_effort_reference": stage.effort,
                        "corpus_context": context,
                        "variant_context": variant_context,
                        "task_description": (
                            f"Perform stage '{stage.name}' requiring skill '{stage.skill}' for "
                            f"the {workload} variant described in variant_context. Respect "
                            f"{len(stage.deps)} upstream dependencies and produce a verifiable stage output."
                        ),
                        "rater1_difficulty": "",
                        "rater1_failure_impact": "",
                        "rater1_confidence": "",
                        "rater1_reason": "",
                        "rater2_difficulty": "",
                        "rater2_failure_impact": "",
                        "rater2_confidence": "",
                        "rater2_reason": "",
                        "rater3_difficulty": "",
                        "rater3_failure_impact": "",
                        "rater3_confidence": "",
                        "rater3_reason": "",
                        "adjudicated_difficulty": "",
                        "adjudication_reason": "",
                    }
                )
    path = output / "expert_label_packet.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    public_fields = [
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
        "ambiguity_score",
        "scope_score",
        "dependency_score",
        "reasoning_score",
        "verification_score",
        "difficulty",
        "failure_impact",
        "confidence",
        "reason",
    ]
    for rater_number, shuffle_seed in (
        (1, 2026092201),
        (2, 2026092202),
        (3, 2026092203),
    ):
        blinded = []
        for row in rows:
            blinded.append(
                {
                    "item_id": row["item_id"],
                    "workload": row["workload"],
                    "variant": row["variant"],
                    "stage": row["stage"],
                    "skill": row["skill"],
                    "dependency_count": row["dependency_count"],
                    "base_effort_reference": row["base_effort_reference"],
                    "corpus_context": row["corpus_context"],
                    "variant_context": row["variant_context"],
                    "task_description": row["task_description"],
                    "ambiguity_score": "",
                    "scope_score": "",
                    "dependency_score": "",
                    "reasoning_score": "",
                    "verification_score": "",
                    "difficulty": "",
                    "failure_impact": "",
                    "confidence": "",
                    "reason": "",
                }
            )
        random.Random(shuffle_seed).shuffle(blinded)
        rater_path = output / f"rater{rater_number}_blinded_packet.csv"
        with rater_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=public_fields)
            writer.writeheader()
            writer.writerows(blinded)
    print(f"wrote {len(rows)} merged-template items and three blinded LLM-rater packets to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
