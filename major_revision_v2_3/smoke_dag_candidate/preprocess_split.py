"""Trusted reference for DAG harness smoke; fits mappings on train only."""

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--ingest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ingest = json.loads(args.ingest.read_text(encoding="utf-8"))
    train = pd.read_csv(args.train)
    validation = pd.read_csv(args.validation)
    if list(train.columns) != ingest["train_columns"]:
        raise ValueError("train schema does not match ingest artifact")
    if list(validation.columns) != ingest["validation_columns"]:
        raise ValueError("validation schema does not match ingest artifact")
    columns = [name for name in train.columns if name not in {"row_id", "target", "timestamp"}]
    mappings = {}
    for column in columns:
        if not pd.api.types.is_numeric_dtype(train[column]):
            values = train[column].fillna("__MISSING__").astype(str)
            mappings[column] = {
                value: index for index, value in enumerate(sorted(values.unique()))
            }
    joblib.dump({"columns": columns, "mappings": mappings}, args.output)


if __name__ == "__main__":
    main()
