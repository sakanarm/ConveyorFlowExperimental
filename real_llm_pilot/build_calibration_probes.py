from __future__ import annotations

import difflib
import hashlib
import json
import math
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUGGY = ROOT / "v2" / "data" / "raw" / "bugs2fix" / "train.buggy.txt"
FIXED = ROOT / "v2" / "data" / "raw" / "bugs2fix" / "train.fixed.txt"
OUTPUT = HERE / "calibration_probes.jsonl"


def ml_probe(probe_id: str, difficulty: int, question: str, expected: dict[str, Any]) -> dict[str, Any]:
    return {
        "probe_id": probe_id,
        "workload_family": "ml_build",
        "source_dataset": "UCI Adult / Beijing Air Quality public-data-derived",
        "difficulty": difficulty,
        "prompt": (
            "You are completing a held-out ML engineering ability probe. "
            "Return one JSON object only, with exactly the requested keys. "
            "Do not include markdown, explanation, or code fences.\n\n" + question
        ),
        "validator_type": "json_expected",
        "expected": expected,
        "numeric_tolerance": 0.01,
    }


def build_ml_probes() -> list[dict[str, Any]]:
    probes = [
        ml_probe(
            "CAL-ML-D1-01", 1,
            "An Adult subgroup has 10,965 records and positive_fraction=0.025718. "
            "Estimate the positive record count by multiplying and rounding to the nearest integer. "
            'Schema: {"positive_records": integer}.',
            {"positive_records": round(10965 * 0.025718)},
        ),
        ml_probe(
            "CAL-ML-D1-02", 1,
            "The Adult dataset has positive_fraction=0.2392817657. A majority-class classifier always "
            "predicts negative. Report accuracy as a percentage rounded to two decimals. "
            'Schema: {"accuracy_percent": number}.',
            {"accuracy_percent": round((1 - 0.2392817657) * 100, 2)},
        ),
        ml_probe(
            "CAL-ML-D1-03", 1,
            "The Beijing dataset has 420,768 rows evenly divided across 12 stations. "
            'Schema: {"rows_per_station": integer}.',
            {"rows_per_station": 420768 // 12},
        ),
        ml_probe(
            "CAL-ML-D1-04", 1,
            "A binary classifier produced TP=42, TN=48, FP=2, FN=8. "
            "Return accuracy rounded to two decimals on the 0-1 scale. "
            'Schema: {"accuracy": number}.',
            {"accuracy": 0.90},
        ),
        ml_probe(
            "CAL-ML-D1-05", 1,
            "For an i.i.d. imbalanced Adult classification task, choose the split that best preserves class ratios. "
            "Options: random, stratified_random, chronological. "
            'Schema: {"split": string}.',
            {"split": "stratified_random"},
        ),
        ml_probe(
            "CAL-ML-D2-01", 2,
            "A model has TP=36, FP=9, FN=12. Return precision, recall, and F1 rounded to four decimals. "
            'Schema: {"precision": number, "recall": number, "f1": number}.',
            {"precision": 0.8, "recall": 0.75, "f1": 0.7742},
        ),
        ml_probe(
            "CAL-ML-D2-02", 2,
            "A classifier has sensitivity=0.80 and specificity=0.90. Return balanced accuracy rounded to two decimals. "
            'Schema: {"balanced_accuracy": number}.',
            {"balanced_accuracy": 0.85},
        ),
        ml_probe(
            "CAL-ML-D2-03", 2,
            "For Beijing hourly PM2.5 forecasting, choose the leakage-safe validation split. "
            "Options: shuffled_kfold, chronological, random_stratified. "
            'Schema: {"split": string}.',
            {"split": "chronological"},
        ),
        ml_probe(
            "CAL-ML-D2-04", 2,
            "Adult subgroup A has 1,000 rows with positive rate 0.10; subgroup B has 500 rows with positive rate 0.40. "
            "Return the combined positive rate rounded to four decimals. "
            'Schema: {"combined_positive_rate": number}.',
            {"combined_positive_rate": 0.2},
        ),
        ml_probe(
            "CAL-ML-D2-05", 2,
            "Choose the only leakage-safe preprocessing sequence. Options: "
            "fit_all_then_split; split_fit_train_transform_both; transform_test_then_split. "
            'Schema: {"sequence": string}.',
            {"sequence": "split_fit_train_transform_both"},
        ),
        ml_probe(
            "CAL-ML-D3-01", 3,
            "Two thresholds give confusion counts. A: TP=72 FP=18 FN=28. B: TP=64 FP=8 FN=36. "
            "Compute each F1 and return the label with the higher F1. "
            'Schema: {"best_threshold": string}.',
            {"best_threshold": "A"},
        ),
        ml_probe(
            "CAL-ML-D3-02", 3,
            "Hyperparameters must be tuned without optimistic bias. Choose the correct nested-validation order. "
            "Options: tune_all_then_outer_split; outer_split_then_inner_tune; inner_tune_then_reuse_test. "
            'Schema: {"procedure": string}.',
            {"procedure": "outer_split_then_inner_tune"},
        ),
        ml_probe(
            "CAL-ML-D3-03", 3,
            "Utility is 5*TP - 2*FP - 6*FN. Model A: TP=80 FP=30 FN=20. "
            "Model B: TP=70 FP=10 FN=30. Return the better model and its utility. "
            'Schema: {"model": string, "utility": integer}.',
            {"model": "A", "utility": 220},
        ),
        ml_probe(
            "CAL-ML-D3-04", 3,
            "Two chronological folds have n1=100, RMSE1=10 and n2=300, RMSE2=20. "
            "Return pooled RMSE=sqrt((n1*RMSE1^2+n2*RMSE2^2)/(n1+n2)), rounded to two decimals. "
            'Schema: {"pooled_rmse": number}.',
            {"pooled_rmse": round(math.sqrt((100 * 10**2 + 300 * 20**2) / 400), 2)},
        ),
        ml_probe(
            "CAL-ML-D3-05", 3,
            "Group A has TP=45 FN=5; Group B has TP=30 FN=10. "
            "Return the absolute equal-opportunity gap |TPR_A-TPR_B| rounded to two decimals. "
            'Schema: {"tpr_gap": number}.',
            {"tpr_gap": 0.15},
        ),
    ]
    return probes


def edit_size(source: str, target: str) -> int:
    source_tokens = source.split()
    target_tokens = target.split()
    matcher = difflib.SequenceMatcher(a=source_tokens, b=target_tokens, autojunk=False)
    total = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            total += max(i2 - i1, j2 - j1)
    return total


def evenly_select(rows: list[tuple[int, str, str, int]], count: int) -> list[tuple[int, str, str, int]]:
    if len(rows) < count:
        raise ValueError(f"need {count} rows, found {len(rows)}")
    positions = [round(i * (len(rows) - 1) / (count - 1)) for i in range(count)]
    return [rows[position] for position in positions]


def build_bug_probes() -> list[dict[str, Any]]:
    buggy = BUGGY.read_text(encoding="utf-8").splitlines()
    fixed = FIXED.read_text(encoding="utf-8").splitlines()
    if len(buggy) != len(fixed):
        raise ValueError("Bugs2Fix paired files have different line counts")

    pools: dict[int, list[tuple[int, str, str, int]]] = {1: [], 2: [], 3: []}
    for index, (source, target) in enumerate(zip(buggy, fixed), start=1):
        if index <= 500 or source == target or not 70 <= len(source) <= 240:
            continue
        changes = edit_size(source, target)
        if 1 <= changes <= 2:
            difficulty = 1
        elif 3 <= changes <= 5:
            difficulty = 2
        elif 6 <= changes <= 14:
            difficulty = 3
        else:
            continue
        pools[difficulty].append((index, source, target, changes))

    probes: list[dict[str, Any]] = []
    for difficulty in (1, 2, 3):
        candidates = sorted(pools[difficulty], key=lambda row: (row[3], row[0]))
        for ordinal, (line_no, source, target, changes) in enumerate(evenly_select(candidates, 5), start=1):
            probes.append({
                "probe_id": f"CAL-BUG-D{difficulty}-{ordinal:02d}",
                "workload_family": "fix_bug",
                "source_dataset": "CodeXGLUE Bugs2Fix small train pair",
                "difficulty": difficulty,
                "prompt": (
                    "You are completing a held-out Java bug-repair ability probe. "
                    "Return only the complete repaired normalized Java function. "
                    "Do not include markdown, explanation, or code fences.\n\n"
                    f"Buggy function:\n{source}"
                ),
                "validator_type": "normalized_exact_repair",
                "expected": target,
                "provenance": {
                    "source_line": line_no,
                    "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                    "target_sha256": hashlib.sha256(target.encode("utf-8")).hexdigest(),
                    "token_edit_size": changes,
                },
            })
    return probes


def main() -> int:
    probes = build_ml_probes() + build_bug_probes()
    counts: dict[tuple[str, int], int] = {}
    for probe in probes:
        key = (probe["workload_family"], probe["difficulty"])
        counts[key] = counts.get(key, 0) + 1
    expected_counts = {(family, difficulty): 5 for family in ("ml_build", "fix_bug") for difficulty in (1, 2, 3)}
    if counts != expected_counts or len({probe["probe_id"] for probe in probes}) != 30:
        raise ValueError(f"unexpected calibration design: {counts}")
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as handle:
        for probe in probes:
            handle.write(json.dumps(probe, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"output": str(OUTPUT), "probes": len(probes), "cells": {str(k): v for k, v in counts.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
