from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LABEL_DIR = ROOT / "expert_labels"


def write_mapping(rows: list[dict], name: str, choose) -> dict:
    output = LABEL_DIR / name
    mapped = []
    changed = 0
    for row in rows:
        votes = [int(row[f"rater{i}_difficulty"]) for i in (1, 2, 3)]
        selected = choose(votes)
        changed += selected != int(row["adjudicated_difficulty"])
        copy = dict(row)
        copy["adjudicated_difficulty"] = str(selected)
        copy["adjudication_reason"] = f"sensitivity mapping from role votes {votes}"
        mapped.append(copy)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(mapped[0]))
        writer.writeheader()
        writer.writerows(mapped)
    return {
        "file": output.name,
        "changed_from_adjudicated": changed,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }


def main() -> int:
    frozen = LABEL_DIR / "llm_difficulty_labels_frozen.csv"
    with frozen.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 304:
        raise SystemExit("expected 304 frozen labels")
    report = {
        "purpose": "Bound annotation uncertainty; not alternative primary analyses.",
        "lower": write_mapping(rows, "llm_difficulty_labels_lower.csv", min),
        "upper": write_mapping(rows, "llm_difficulty_labels_upper.csv", max),
    }
    (LABEL_DIR / "llm_mapping_sensitivity.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
