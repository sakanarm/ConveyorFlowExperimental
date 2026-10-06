"""Trusted container-only smoke candidate; not an LLM result."""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor


def prepare(frame: pd.DataFrame, columns: list[str], mappings: dict | None = None):
    mappings = {} if mappings is None else mappings
    result = pd.DataFrame(index=frame.index)
    for column in columns:
        values = frame[column]
        if pd.api.types.is_numeric_dtype(values):
            result[column] = pd.to_numeric(values, errors="coerce")
        else:
            strings = values.fillna("__MISSING__").astype(str)
            if column not in mappings:
                mappings[column] = {value: index for index, value in enumerate(sorted(strings.unique()))}
            result[column] = strings.map(mappings[column]).fillna(-1).astype(float)
    return result, mappings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--output-model", type=Path, required=True)
    args = parser.parse_args()
    train = pd.read_csv(args.train)
    validation = pd.read_csv(args.validation)
    columns = [name for name in train.columns if name not in {"row_id", "target", "timestamp"}]
    if list(train.columns) != list(validation.columns):
        raise ValueError("train/validation schema mismatch")
    x, mappings = prepare(train, columns)
    y = pd.to_numeric(train["target"], errors="raise")
    classification = set(y.unique()) <= {0, 1}
    if classification:
        model = HistGradientBoostingClassifier(max_iter=90, max_leaf_nodes=31, random_state=23)
    else:
        model = HistGradientBoostingRegressor(max_iter=90, max_leaf_nodes=31, random_state=23)
    model.fit(x, y)
    joblib.dump({"model": model, "columns": columns, "mappings": mappings,
                 "classification": classification}, args.output_model)


if __name__ == "__main__":
    main()
