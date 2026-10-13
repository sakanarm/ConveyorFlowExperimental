"""Trusted no-provider Covertype DAG integration fixture, not an LLM answer."""

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier


def prepare(frame, columns, mappings):
    result = pd.DataFrame(index=frame.index)
    for column in columns:
        if column in mappings:
            result[column] = frame[column].fillna("__MISSING__").astype(str).map(
                mappings[column]).fillna(-1).astype(float)
        else:
            result[column] = pd.to_numeric(frame[column], errors="coerce")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--preprocessor", type=Path, required=True)
    parser.add_argument("--output-model", type=Path, required=True)
    args = parser.parse_args()
    train, validation = pd.read_csv(args.train), pd.read_csv(args.validation)
    if list(train.columns) != list(validation.columns):
        raise ValueError("development schemas differ")
    state = joblib.load(args.preprocessor)
    model = ExtraTreesClassifier(n_estimators=48, max_depth=20,
                                 min_samples_leaf=2, n_jobs=2,
                                 random_state=20261011)
    model.fit(prepare(train, state["columns"], state["mappings"]), train["target"])
    # The inherited compatibility interface calls this flag "classification"
    # but defines it as *binary* classification. False selects predict(),
    # which is also correct for this seven-class task.
    joblib.dump({**state, "model": model, "classification": False}, args.output_model)


if __name__ == "__main__":
    main()
