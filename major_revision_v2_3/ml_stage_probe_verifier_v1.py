"""TRUSTED verifier, invoked ONLY in a networkless candidate container.

The deliberately narrow ordinal-encoding artifact interface is public. It
tests training-only category state and interoperability, not unrestricted
AutoML or every possible leakage mechanism in arbitrary candidate source.
"""
import argparse
import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator


def expected_state(train):
    columns = [c for c in train.columns if c not in {"row_id", "target", "timestamp"}]
    mappings = {}
    for c in columns:
        if not pd.api.types.is_numeric_dtype(train[c]):
            mappings[c] = {v: i for i, v in enumerate(sorted(train[c].fillna("__MISSING__").astype(str).unique()))}
    return {"columns": columns, "mappings": mappings}


def transform(frame, state):
    result = pd.DataFrame(index=frame.index)
    for c in state["columns"]:
        if c in state["mappings"]:
            result[c] = frame[c].fillna("__MISSING__").astype(str).map(state["mappings"][c]).fillna(-1).astype(float)
        else:
            result[c] = pd.to_numeric(frame[c], errors="coerce").astype(float)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("preprocess", "train"), required=True)
    stage = parser.parse_args().stage
    train = pd.read_csv("/input/train.csv")
    expected = expected_state(train)
    path = "/artifact/preprocessor.joblib" if stage == "preprocess" else "/artifact/model.joblib"
    state = joblib.load(path)
    keys = {"columns", "mappings"} if stage == "preprocess" else {"columns", "mappings", "model", "classification"}
    if not isinstance(state, dict) or set(state) != keys:
        raise ValueError("artifact keys differ from the public frozen ordinal-state interface")
    if state["columns"] != expected["columns"] or state["mappings"] != expected["mappings"]:
        raise ValueError("columns/category mappings do not match training-only frozen interface")
    for split in ("train", "validation", "test_features"):
        x = transform(pd.read_csv("/input/" + split + ".csv"), state)
        if x.shape[1] != len(expected["columns"]) or np.isinf(x.to_numpy()).any():
            raise ValueError("public transform has invalid shape or infinities")
    if stage == "train":
        classification = set(pd.to_numeric(train["target"], errors="raise").unique()) <= {0, 1}
        if type(state["classification"]) is not bool or state["classification"] != classification:
            raise ValueError("classification flag invalid")
        if not isinstance(state["model"], BaseEstimator):
            raise ValueError("must save an importable sklearn estimator")
        test = pd.read_csv("/input/test_features.csv")
        x = transform(test, state)
        prediction = state["model"].predict_proba(x)[:, 1] if classification else state["model"].predict(x)
        pd.DataFrame({"row_id": test["row_id"], "prediction": prediction}).to_csv("/out/predictions.csv", index=False)
    print("FROZEN_ARTIFACT_INTERFACE_PASS")


if __name__ == "__main__":
    main()
