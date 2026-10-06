"""Score container-produced predictions without executing candidate code."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from reference_ml_gates import roc_auc


HERE = Path(__file__).resolve().parent
CASES = HERE / "ml_cases"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        return fields, list(reader)


def score(case_id: str, prediction_path: Path, model_artifact: Path | None = None) -> dict:
    gate_path = CASES / "quality_gates.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate["status"] != "frozen_before_provider_calls":
        raise ValueError("quality gate is not frozen")
    case = next((item for item in gate["cases"] if item["case_id"] == case_id), None)
    if case is None:
        raise ValueError(f"unknown case {case_id}")
    _, labels = read_csv(CASES / "hidden" / case["corpus"] / "test_labels.csv")
    output = {
        "case_id": case_id,
        "gate_sha256": sha256(gate_path),
        "prediction_sha256": sha256(prediction_path) if prediction_path.is_file() else None,
        "expected_rows": len(labels),
        "structural_pass": False,
        "quality_pass": False,
        "verified": False,
    }
    try:
        fields, predictions = read_csv(prediction_path)
        if fields != ["row_id", "prediction"]:
            raise ValueError("predictions.csv must have exactly row_id,prediction columns")
        if len(predictions) != len(labels):
            raise ValueError("prediction row count differs from hidden test count")
        lookup = {}
        for row in predictions:
            row_id = row["row_id"]
            if row_id in lookup:
                raise ValueError("duplicate prediction row ID")
            value = float(row["prediction"])
            if not math.isfinite(value):
                raise ValueError("predictions must be finite")
            lookup[row_id] = value
        expected = {row["row_id"] for row in labels}
        if set(lookup) != expected:
            raise ValueError("prediction row IDs do not match hidden test rows")
        truth = np.fromiter((float(row["target"]) for row in labels), dtype=float)
        predicted = np.fromiter((lookup[row["row_id"]] for row in labels), dtype=float)
        if case["corpus"] == "adult" and (predicted.min() < 0 or predicted.max() > 1):
            raise ValueError("Adult predictions must be probabilities in [0,1]")
        if model_artifact is not None and (
            not model_artifact.is_file() or model_artifact.stat().st_size == 0
        ):
            raise ValueError("trained model artifact missing or empty")
        output["structural_pass"] = True
        if case["corpus"] == "adult":
            value = float(roc_auc(truth, predicted))
            threshold = float(case["quality"]["quality_floor"])
            passed = value >= threshold
        else:
            value = float(np.abs(truth - predicted).mean())
            threshold = float(case["quality"]["quality_ceiling"])
            passed = value <= threshold
        output.update({
            "metric": case["quality"]["metric"],
            "score": value,
            "threshold": threshold,
            "quality_pass": passed,
            "verified": passed and model_artifact is not None,
            "model_artifact_sha256": sha256(model_artifact) if model_artifact else None,
        })
    except (OSError, ValueError, KeyError) as error:
        output["failure_reason"] = str(error)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--model-artifact", type=Path)
    args = parser.parse_args()
    print(json.dumps(score(args.case_id, args.predictions, args.model_artifact), indent=2))


if __name__ == "__main__":
    main()
