"""Trusted Covertype 7-class reference: train only, validation only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import accuracy_score, f1_score


LABELS = list(range(1, 8))


def probe(data: Path) -> dict:
    train = pd.read_csv(data / "train.csv")
    validation = pd.read_csv(data / "validation.csv")
    if (len(train) != 407_058 or len(validation) != 86_698 or
            list(train.columns) != list(validation.columns) or
            list(train.columns)[0] != "row_id" or list(train.columns)[-1] != "target" or
            len(train.columns) != 56):
        raise ValueError("Covertype public data contract drift")
    columns = list(train.columns)[1:-1]
    for frame in (train, validation):
        if frame[columns].isna().any().any() or not frame["target"].isin(LABELS).all():
            raise ValueError("Covertype features/labels not complete")
    y_train = train["target"].to_numpy()
    y_val = validation["target"].to_numpy()
    majority = int(train["target"].value_counts().idxmax())
    dummy = [majority] * len(validation)
    dummy_macro = float(f1_score(y_val, dummy, average="macro", labels=LABELS,
                                 zero_division=0))
    model = ExtraTreesClassifier(n_estimators=48, max_depth=20,
                                 min_samples_leaf=2, n_jobs=2,
                                 random_state=20261011)
    model.fit(train[columns], y_train)
    predicted = model.predict(validation[columns])
    return {"status": "trusted_reference_validation_only", "corpus": "covertype",
            "metric": "macro_f1", "validation_macro_f1": float(f1_score(
                y_val, predicted, average="macro", labels=LABELS, zero_division=0)),
            "validation_accuracy": float(accuracy_score(y_val, predicted)),
            "dummy_majority_class": majority, "dummy_macro_f1": dummy_macro,
            "train_rows": len(train), "validation_rows": len(validation),
            "class_domain": LABELS, "hidden_test_opened": False,
            "model": "ExtraTreesClassifier(n_estimators=48,max_depth=20,min_samples_leaf=2,n_jobs=2,random_state=20261011)",
            "provider_calls": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(probe(args.data), sort_keys=True))
