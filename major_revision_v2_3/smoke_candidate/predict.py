"""Trusted container-only smoke candidate; not an LLM result."""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd

from train_model import prepare


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--output-predictions", type=Path, required=True)
    args = parser.parse_args()
    state = joblib.load(args.model)
    test = pd.read_csv(args.test)
    x, _ = prepare(test, state["columns"], state["mappings"])
    model = state["model"]
    prediction = model.predict_proba(x)[:, 1] if state["classification"] else model.predict(x)
    pd.DataFrame({"row_id": test["row_id"], "prediction": prediction}).to_csv(
        args.output_predictions, index=False
    )


if __name__ == "__main__":
    main()
