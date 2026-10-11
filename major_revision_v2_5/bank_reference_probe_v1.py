"""Trusted Bank Marketing baseline trained on train, scored on validation only."""

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


def probe(data: Path) -> dict:
    train = pd.read_csv(data / "train.csv")
    validation = pd.read_csv(data / "validation.csv")
    if (len(train) != 31_647 or len(validation) != 6_782 or
            set(train.columns) != set(validation.columns) or
            "duration" in train.columns or "duration" in validation.columns):
        raise ValueError("Bank data contract drift or duration leakage")
    columns = [name for name in train.columns if name not in ("row_id", "target")]
    categorical = [name for name in columns if name not in NUMERIC]
    if len(columns) != 15 or len(categorical) != 9:
        raise ValueError("Bank feature schema changed")
    for frame in (train, validation):
        if not frame["target"].isin([0, 1]).all():
            raise ValueError("target must be binary")
    preprocess = ColumnTransformer([
        ("numeric", Pipeline([("impute", SimpleImputer(strategy="median")),
                               ("scale", StandardScaler())]), NUMERIC),
        ("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                                   ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical),
    ])
    model = Pipeline([("preprocess", preprocess),
                      ("model", LogisticRegression(solver="liblinear", max_iter=1000,
                                                   class_weight="balanced", random_state=20261011))])
    model.fit(train[columns], train["target"])
    probability = model.predict_proba(validation[columns])[:, 1]
    return {"status": "trusted_reference_validation_only", "corpus": "bank",
            "metric": "roc_auc", "validation_roc_auc": float(roc_auc_score(validation["target"], probability)),
            "train_rows": len(train), "validation_rows": len(validation),
            "train_positive": int(train["target"].sum()),
            "validation_positive": int(validation["target"].sum()),
            "post_call_duration_excluded": True, "hidden_test_opened": False,
            "model": "LogisticRegression(liblinear, class_weight=balanced, max_iter=1000) with train-fitted imputation/scaling/one-hot",
            "provider_calls": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(probe(args.data), sort_keys=True))
