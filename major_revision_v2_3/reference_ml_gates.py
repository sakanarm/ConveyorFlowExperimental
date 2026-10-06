"""Freeze trusted, NumPy-only reference quality gates before provider calls."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
CASES = HERE / "ml_cases"
MISSING = {"", "NA", "NAN", "NULL", "?"}
ADULT_NUMERIC = {
    "age", "fnlwgt", "education_num", "capital_gain", "capital_loss", "hours_per_week"
}
BEIJING_CATEGORICAL = {"wd", "station"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def roc_auc(labels: np.ndarray, scores: np.ndarray) -> float:
    order = np.argsort(scores, kind="stable")
    sorted_scores = scores[order]
    sorted_labels = labels[order]
    positive = int(labels.sum())
    negative = len(labels) - positive
    if not positive or not negative:
        raise ValueError("ROC AUC needs both classes")
    rank_sum = 0.0
    first = 0
    while first < len(labels):
        last = first + 1
        while last < len(labels) and sorted_scores[last] == sorted_scores[first]:
            last += 1
        mean_rank = (first + 1 + last) / 2
        rank_sum += mean_rank * float(sorted_labels[first:last].sum())
        first = last
    return (rank_sum - positive * (positive + 1) / 2) / (positive * negative)


def features_for(case: dict, sample_row: dict) -> list[str]:
    return [
        column for column in sample_row
        if column not in {"row_id", "target", "timestamp", *case["excluded_features"]}
    ]


def design_matrix(
    training: list[dict[str, str]], test: list[dict[str, str]], features: list[str], corpus: str
) -> tuple[np.ndarray, np.ndarray]:
    if corpus == "adult":
        numeric = [feature for feature in features if feature in ADULT_NUMERIC]
        categorical = [feature for feature in features if feature not in ADULT_NUMERIC]
    else:
        categorical = [feature for feature in features if feature in BEIJING_CATEGORICAL]
        numeric = [feature for feature in features if feature not in BEIJING_CATEGORICAL]
    numeric_stats = {}
    for feature in numeric:
        values = np.fromiter(
            (
                float(row[feature])
                for row in training
                if row[feature].strip().upper() not in MISSING
            ), dtype=float,
        )
        if not len(values):
            raise ValueError(f"all training values missing in {feature}")
        numeric_stats[feature] = (float(values.mean()), max(float(values.std()), 1e-8))
    vocab = {
        feature: sorted({row[feature] for row in training if row[feature].strip().upper() not in MISSING})
        for feature in categorical
    }
    offsets = {}
    cursor = 1 + len(numeric)
    for feature in categorical:
        offsets[feature] = {value: cursor + index for index, value in enumerate(vocab[feature])}
        cursor += len(vocab[feature])

    def encode(rows: list[dict[str, str]]) -> np.ndarray:
        matrix = np.zeros((len(rows), cursor), dtype=np.float64)
        matrix[:, 0] = 1.0
        for index, row in enumerate(rows):
            for column, feature in enumerate(numeric, start=1):
                value = row[feature].strip()
                if value.upper() not in MISSING:
                    mean, scale = numeric_stats[feature]
                    matrix[index, column] = (float(value) - mean) / scale
            for feature in categorical:
                column = offsets[feature].get(row[feature])
                if column is not None:
                    matrix[index, column] = 1.0
        return matrix

    return encode(training), encode(test)


def evaluate_case(case: dict) -> tuple[dict, list[dict]]:
    corpus = case["corpus"]
    source = CASES / "data" / corpus
    training = read_csv(source / "train.csv")
    test = read_csv(source / "test_features.csv")
    labels = read_csv(CASES / "hidden" / corpus / "test_labels.csv")
    if len(test) != len(labels) or any(
        row["row_id"] != label["row_id"] for row, label in zip(test, labels)
    ):
        raise AssertionError("test rows and hidden labels are misaligned")
    features = features_for(case, training[0])
    x_train, x_test = design_matrix(training, test, features, corpus)
    y_train = np.fromiter((float(row["target"]) for row in training), dtype=float)
    y_test = np.fromiter((float(row["target"]) for row in labels), dtype=float)
    ridge = np.eye(x_train.shape[1]) * 1.0
    ridge[0, 0] = 0.0
    weights = np.linalg.solve(x_train.T @ x_train + ridge, x_train.T @ y_train)
    prediction = x_test @ weights
    if corpus == "adult":
        prediction = np.clip(prediction, 0.0, 1.0)
        reference = roc_auc(y_test, prediction)
        dummy = 0.5
        if reference <= dummy:
            raise AssertionError("Adult reference did not outperform dummy")
        quality = {
            "metric": "roc_auc",
            "direction": "higher_is_better",
            "dummy_score": dummy,
            "reference_score": reference,
            "quality_floor": dummy + 0.50 * (reference - dummy),
            "rule": "at least half the reference ROC-AUC improvement over 0.5",
        }
    else:
        reference = float(np.abs(y_test - prediction).mean())
        dummy = float(np.abs(y_test - np.median(y_train)).mean())
        if reference >= dummy:
            raise AssertionError("Beijing reference did not outperform dummy")
        quality = {
            "metric": "mean_absolute_error",
            "direction": "lower_is_better",
            "dummy_score": dummy,
            "reference_score": reference,
            "quality_ceiling": dummy - 0.50 * (dummy - reference),
            "rule": "at least half the reference MAE reduction versus train-median dummy",
        }
    predicted_rows = [
        {"row_id": row["row_id"], "prediction": float(value)}
        for row, value in zip(test, prediction)
    ]
    return {"features": features, "quality": quality}, predicted_rows


def main() -> None:
    manifest_path = CASES / "case_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["status"] != "pilot_inputs_prepared_not_executed":
        raise ValueError("case inputs are not in pilot-prepared state")
    reference_dir = CASES / "reference"
    reference_dir.mkdir(parents=True, exist_ok=True)
    output = []
    for case in manifest["variants"]:
        evidence, predictions = evaluate_case(case)
        path = reference_dir / f"{case['case_id']}_predictions.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["row_id", "prediction"])
            writer.writeheader()
            writer.writerows(predictions)
        output.append({
            "case_id": case["case_id"],
            "corpus": case["corpus"],
            "excluded_features": case["excluded_features"],
            **evidence,
            "reference_predictions_sha256": sha256(path),
        })
        print(
            f"{case['case_id']}: {evidence['quality']['metric']}="
            f"{evidence['quality']['reference_score']:.5f}", flush=True
        )
    gate = {
        "status": "frozen_before_provider_calls",
        "research_results": False,
        "case_manifest_sha256": sha256(manifest_path),
        "reference_script_sha256": sha256(Path(__file__)),
        "cases": output,
    }
    path = CASES / "quality_gates.json"
    path.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    print(f"gate_file={path} sha256={sha256(path)}")


if __name__ == "__main__":
    main()
