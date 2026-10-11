"""Trusted Bank binary verifier, isolated from candidate model execution."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_values(path: Path, name: str) -> dict[str, str]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["row_id", name]:
            raise ValueError(f"Expected row_id,{name} columns")
        result = {}
        for row in reader:
            if (None in row or row["row_id"] is None or row[name] is None or
                    not row["row_id"].startswith("bank_") or row["row_id"] in result):
                raise ValueError("Missing/duplicate/invalid Bank row")
            result[row["row_id"]] = row[name]
    return result


def roc_auc(truth: list[int], prediction: list[float]) -> float:
    if len(truth) != len(prediction) or not truth:
        raise ValueError("Truth/prediction length mismatch")
    positives = sum(truth)
    negatives = len(truth) - positives
    if not positives or not negatives:
        raise ValueError("ROC-AUC requires both classes")
    ordered = sorted(zip(prediction, truth))
    rank_sum = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][0] == ordered[index][0]:
            end += 1
        average_rank = (index + 1 + end) / 2
        rank_sum += average_rank * sum(label for _, label in ordered[index:end])
        index = end
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def score(predictions: Path, hidden_labels: Path, gate_path: Path,
          model_artifact: Path | None) -> dict:
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if (gate.get("status") != "quality_gate_frozen_before_hidden_test_and_provider_calls" or
            gate.get("corpus") != "bank" or gate.get("metric") != "roc_auc" or
            gate.get("provider_calls") != 0):
        raise ValueError("Bank quality gate identity changed")
    result = {"status": "candidate_verification",
              "prediction_sha256": sha256(predictions) if predictions.is_file() else None,
              "gate_sha256": sha256(gate_path), "structural_pass": False,
              "quality_pass": False, "verified": False, "provider_calls": 0}
    try:
        if (model_artifact is None or not model_artifact.is_file() or
                not 0 < model_artifact.stat().st_size <= 268435456 or
                not predictions.is_file() or predictions.stat().st_size > 32000000):
            raise ValueError("Missing/oversize model or prediction artifact")
        truth_map = read_values(hidden_labels, "target")
        pred_map = read_values(predictions, "prediction")
        if len(truth_map) != 6782 or truth_map.keys() != pred_map.keys():
            raise ValueError("Prediction row IDs differ from hidden Bank test")
        truth, prediction = [], []
        for row_id, label in truth_map.items():
            if label not in ("0", "1"):
                raise ValueError("Bank target must be binary")
            value = float(pred_map[row_id])
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("Bank prediction must be finite probability [0,1]")
            truth.append(int(label))
            prediction.append(value)
        result["structural_pass"] = True
        value = roc_auc(truth, prediction)
        floor = float(gate["quality_floor"])
        result.update(metric="roc_auc", score=value, threshold=floor,
                      quality_pass=value >= floor, verified=value >= floor,
                      expected_rows=len(truth),
                      model_artifact_sha256=sha256(model_artifact))
    except (OSError, ValueError, KeyError, TypeError) as error:
        result["failure_reason"] = str(error)
    return result


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--predictions", type=Path, required=True)
    cli.add_argument("--hidden-labels", type=Path, required=True)
    cli.add_argument("--gate", type=Path, required=True)
    cli.add_argument("--model-artifact", type=Path, required=True)
    args = cli.parse_args()
    print(json.dumps(score(args.predictions, args.hidden_labels, args.gate,
                           args.model_artifact), sort_keys=True))
