"""Trusted Covertype model emits predictions/artifact; never reads test labels."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def run(data: Path, output: Path) -> dict:
    train = pd.read_csv(data / "train.csv")
    test = pd.read_csv(data / "test_features.csv")
    if (len(train) != 407_058 or len(test) != 87_256 or
            list(train.columns)[:-1] != list(test.columns) or
            len(test.columns) != 55 or "target" in test.columns):
        raise ValueError("Covertype public test input drift")
    columns = list(test.columns)[1:]
    model = ExtraTreesClassifier(n_estimators=48, max_depth=20,
                                 min_samples_leaf=2, n_jobs=2,
                                 random_state=20261011)
    model.fit(train[columns], train["target"])
    predictions = model.predict(test[columns])
    path = output / "predictions.csv"
    artifact = output / "model.joblib"
    if path.exists() or artifact.exists():
        raise FileExistsError("trusted outputs already exist")
    pd.DataFrame({"row_id": test["row_id"], "prediction": predictions}).to_csv(path, index=False)
    joblib.dump(model, artifact, compress=3)
    return {"status": "trusted_reference_predictions_written_no_test_labels",
            "train_rows": len(train), "test_rows": len(test),
            "prediction_sha256": sha256(path), "model_artifact_sha256": sha256(artifact),
            "test_labels_opened": False, "provider_calls": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.data, args.output), sort_keys=True))
