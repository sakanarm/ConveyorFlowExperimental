"""Trusted, separate 7-class verifier for Covertype candidate predictions.

Candidate containers receive public train/validation/test_features only.  This
verifier runs outside the candidate sandbox with hidden labels after execution.
It does not change the v2.3 binary/regression scorer.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


LABELS = tuple(str(value) for value in range(1, 8))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_two_columns(path: Path, value_column: str) -> dict[str, str]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["row_id", value_column]:
            raise ValueError(f"{path.name}: expected row_id,{value_column} header")
        values = {}
        for row in reader:
            if None in row or row["row_id"] is None or row[value_column] is None:
                raise ValueError(f"{path.name}: malformed CSV row")
            row_id, value = row["row_id"], row[value_column]
            if not row_id.startswith("covertype_") or row_id in values:
                raise ValueError(f"{path.name}: invalid or duplicate row ID")
            if value not in LABELS:
                raise ValueError(f"{path.name}: label must be an integer 1..7")
            values[row_id] = value
    return values


def macro_f1(truth: dict[str, str], prediction: dict[str, str]) -> float:
    if not truth or truth.keys() != prediction.keys():
        raise ValueError("test row IDs differ")
    scores = []
    for label in LABELS:
        tp = sum(truth[key] == label and prediction[key] == label for key in truth)
        fp = sum(truth[key] != label and prediction[key] == label for key in truth)
        fn = sum(truth[key] == label and prediction[key] != label for key in truth)
        denom = 2 * tp + fp + fn
        scores.append(2 * tp / denom if denom else 0.0)
    return sum(scores) / len(LABELS)


def score(predictions: Path, hidden_labels: Path, gate_path: Path,
          model_artifact: Path | None) -> dict:
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if (gate.get("status") != "quality_gate_frozen_before_hidden_test_and_provider_calls" or
            gate.get("corpus") != "covertype" or gate.get("metric") != "macro_f1" or
            gate.get("provider_calls") != 0):
        raise ValueError("Covertype quality gate is not frozen")
    output = {"status": "candidate_verification", "prediction_sha256":
              sha256(predictions) if predictions.is_file() else None,
              "gate_sha256": sha256(gate_path), "structural_pass": False,
              "quality_pass": False, "verified": False, "provider_calls": 0}
    try:
        truth = read_two_columns(hidden_labels, "target")
        predicted = read_two_columns(predictions, "prediction")
        if len(truth) != gate["expected_test_rows"] or truth.keys() != predicted.keys():
            raise ValueError("prediction row count or IDs differ from hidden test")
        if model_artifact is None or not model_artifact.is_file() or model_artifact.stat().st_size == 0:
            raise ValueError("trained model artifact missing or empty")
        output["structural_pass"] = True
        value = macro_f1(truth, predicted)
        floor = float(gate["quality_floor"])
        output.update(metric="macro_f1", score=value, threshold=floor,
                      quality_pass=value >= floor, verified=value >= floor,
                      model_artifact_sha256=sha256(model_artifact),
                      expected_rows=len(truth))
    except (OSError, ValueError, KeyError) as error:
        output["failure_reason"] = str(error)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--hidden-labels", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--model-artifact", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(score(args.predictions, args.hidden_labels, args.gate,
                           args.model_artifact), sort_keys=True))
