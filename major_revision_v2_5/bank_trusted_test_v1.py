"""One-time trusted Bank test sanity check after freezing validation quality gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


NUMERIC = ["age", "balance", "day", "campaign", "pdays", "previous"]


def test(public: Path, hidden: Path) -> dict:
    train = pd.read_csv(public / "train.csv")
    features = pd.read_csv(public / "test_features.csv")
    labels = pd.read_csv(hidden / "test_labels.csv")
    if (len(train) != 31_647 or len(features) != 6_782 or len(labels) != 6_782 or
            "duration" in train.columns or "duration" in features.columns or
            list(labels.columns) != ["row_id", "target"] or
            not features["row_id"].equals(labels["row_id"])):
        raise ValueError("Bank trusted test contract drift")
    columns = [name for name in train.columns if name not in ("row_id", "target")]
    categorical = [name for name in columns if name not in NUMERIC]
    if len(columns) != 15 or len(categorical) != 9:
        raise ValueError("Bank feature schema changed")
    model = Pipeline([
        ("preprocess", ColumnTransformer([
            ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")),
                                   ("scale", StandardScaler())]), NUMERIC),
            ("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                                       ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical),
        ])),
        ("model", LogisticRegression(solver="liblinear", max_iter=1000,
                                     class_weight="balanced", random_state=20261011)),
    ])
    model.fit(train[columns], train["target"])
    prediction = model.predict_proba(features[columns])[:, 1]
    return {"status": "trusted_reference_hidden_test_sanity_only", "corpus": "bank",
            "metric": "roc_auc", "test_roc_auc": float(roc_auc_score(labels["target"], prediction)),
            "train_rows": len(train), "test_rows": len(features),
            "test_positive": int(labels["target"].sum()),
            "hidden_test_opened_only_in_trusted_verifier": True,
            "candidate_test_labels_exposed": False, "provider_calls": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public", type=Path, required=True)
    parser.add_argument("--hidden", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(test(args.public, args.hidden), sort_keys=True))
