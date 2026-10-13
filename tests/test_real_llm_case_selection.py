from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_selected_cases_have_nonempty_public_data_strata() -> None:
    frame = pd.read_csv(ROOT / "real_llm_pilot" / "case_manifest.csv")
    assert len(frame) == 60
    assert not frame["case_id"].duplicated().any()
    assert all(int(json.loads(value).get("records", 1)) > 0 for value in frame["variant_context"])
    counts = frame.groupby(["workload", "adjudicated_difficulty"]).size().to_dict()
    assert all(counts[(workload, difficulty)] == target for workload in (
        "adult_ml", "beijing_ml", "bugs2fix"
    ) for difficulty, target in ((1, 6), (2, 7), (3, 7)))
