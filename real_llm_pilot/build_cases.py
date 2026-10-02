from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "expert_labels" / "llm_difficulty_labels_frozen.csv"
OUTPUT = Path(__file__).resolve().parent / "case_manifest.csv"


def select_workload(frame: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    frame = frame[
        frame["variant_context"].map(
            lambda value: int(json.loads(value).get("records", 1)) > 0
        )
    ].copy()
    frame = frame.sort_values(["adjudicated_difficulty", "variant", "stage", "item_id"]).copy()
    target = {1: 6, 2: 7, 3: 7}
    selected = []
    for difficulty, count in target.items():
        candidates = frame[frame["adjudicated_difficulty"] == difficulty]
        if len(candidates) < count:
            raise ValueError(f"insufficient D{difficulty} cases")
        positions = [round(i * (len(candidates) - 1) / max(1, count - 1)) for i in range(count)]
        selected.append(candidates.iloc[positions])
    result = pd.concat(selected, ignore_index=True)
    if len(result) != n or result["item_id"].duplicated().any():
        raise ValueError("case selection failed uniqueness/count check")
    return result


def main() -> int:
    source = pd.read_csv(SOURCE)
    blocks = []
    for workload in ("adult_ml", "beijing_ml", "bugs2fix"):
        blocks.append(select_workload(source[source["workload"] == workload]))
    cases = pd.concat(blocks, ignore_index=True)
    cases.insert(0, "case_id", [f"RLLM{i:03d}" for i in range(1, len(cases) + 1)])
    cases["execution_bundle"] = "FILL_BEFORE_EXECUTION"
    cases["validator_command"] = "FILL_BEFORE_EXECUTION"
    cases["executable_ready"] = False
    columns = [
        "case_id", "item_id", "workload", "variant", "stage", "skill",
        "dependency_count", "adjudicated_difficulty", "task_description",
        "corpus_context", "variant_context", "execution_bundle",
        "validator_command", "executable_ready",
    ]
    cases[columns].to_csv(OUTPUT, index=False, quoting=csv.QUOTE_MINIMAL)
    counts = cases.groupby(["workload", "adjudicated_difficulty"]).size()
    print(counts.to_string())
    print(f"wrote {len(cases)} specification cases to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
