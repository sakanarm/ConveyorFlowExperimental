from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LABEL_DIR = ROOT / "expert_labels"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    frozen = LABEL_DIR / "llm_difficulty_labels_frozen.csv"
    with frozen.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 304 or len({row["item_id"] for row in rows}) != 304:
        raise SystemExit("expected 304 rows and 304 unique item IDs")
    invalid = [
        row["item_id"]
        for row in rows
        if row["adjudicated_difficulty"].strip() not in {"1", "2", "3"}
    ]
    if invalid:
        raise SystemExit(f"invalid adjudicated labels: {invalid[:5]}")
    unanimous_errors = []
    missing_disagreement_reasons = []
    for row in rows:
        votes = [row[f"rater{i}_difficulty"].strip() for i in (1, 2, 3)]
        final = row["adjudicated_difficulty"].strip()
        if len(set(votes)) == 1 and final != votes[0]:
            unanimous_errors.append(row["item_id"])
        if len(set(votes)) > 1 and not row["adjudication_reason"].strip():
            missing_disagreement_reasons.append(row["item_id"])
    if unanimous_errors:
        raise SystemExit(f"unanimous labels changed: {unanimous_errors[:5]}")
    if missing_disagreement_reasons:
        raise SystemExit(f"missing adjudication reasons: {missing_disagreement_reasons[:5]}")

    distribution = Counter(int(row["adjudicated_difficulty"]) for row in rows)
    class_share = {str(level): distribution[level] / len(rows) for level in (1, 2, 3)}
    agreement = json.loads(
        (LABEL_DIR / "expert_label_agreement.json").read_text(encoding="utf-8")
    )
    workload_kappas = [
        pair["quadratic_weighted_kappa"]
        for workload in agreement["pairwise_agreement_by_workload"].values()
        for pair in workload.values()
    ]
    checks = {
        "row_and_id_integrity": True,
        "all_items_adjudicated": True,
        "unanimous_items_preserved": True,
        "disagreement_reasons_complete": True,
        "minimum_pairwise_kappa_at_least_0_70": (
            agreement["minimum_pairwise_quadratic_weighted_kappa"] >= 0.70
        ),
        "each_class_at_least_10_percent": all(value >= 0.10 for value in class_share.values()),
    }
    validation = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "items": len(rows),
        "checks": checks,
        "adjudicated_distribution": dict(sorted(distribution.items())),
        "adjudicated_class_share": class_share,
        "diagnostics": {
            "minimum_workload_pairwise_kappa": min(workload_kappas),
            "subgroup_review_required": min(workload_kappas) < 0.70,
            "interpretation": "Overall gate is primary; subgroup review is reported and bounded by alternate mappings.",
        },
        "frozen_sha256": sha256(frozen),
    }
    (LABEL_DIR / "llm_annotation_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    manifest_files = [
        ROOT / "docs" / "EXPERT_LABEL_PROTOCOL.md",
        ROOT / "docs" / "DIFFICULTY_RUBRIC.md",
        ROOT / "docs" / "LLM_ANNOTATION_CLAIM.md",
        ROOT / "docs" / "LLM_ANNOTATION_PROMPTS.md",
        ROOT / "data" / "manifest.json",
        ROOT / "data" / "derived" / "annotation_variants.json",
        *(LABEL_DIR / f"rater{i}_blinded_packet.csv" for i in (1, 2, 3)),
        LABEL_DIR / "expert_labels_merged.csv",
        LABEL_DIR / "expert_label_agreement.json",
        frozen,
        LABEL_DIR / "llm_difficulty_labels_lower.csv",
        LABEL_DIR / "llm_difficulty_labels_upper.csv",
        LABEL_DIR / "llm_mapping_sensitivity.json",
    ]
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "annotation_method": "three blinded role-conditioned passes plus separate adjudication",
        "underlying_model": "OpenAI Codex GPT-5-family session; exact deployment snapshot not exposed",
        "independence_warning": "Same-model passes; do not describe as independent experts.",
        "roles": [
            "ML Methodologist",
            "Software Reliability Reviewer",
            "Workflow/Resource Reviewer",
            "Senior Methods Adjudicator",
        ],
        "file_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path)
            for path in manifest_files
        },
    }
    (LABEL_DIR / "llm_annotation_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0 if validation["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
