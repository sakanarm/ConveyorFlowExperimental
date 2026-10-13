"""Materialize 60 deterministic public-data Real-LLM task bundles."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import shutil
import statistics
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT / "data" / "raw"
MANIFEST = HERE / "case_manifest.csv"
BUNDLES = HERE / "case_bundles"
VALIDATOR_SOURCE = HERE / "case_bundle_validator.py"


ADULT_COLUMNS = [
    "age", "workclass", "fnlwgt", "education", "education_num", "marital_status",
    "occupation", "relationship", "race", "sex", "capital_gain", "capital_loss",
    "hours_per_week", "native_country", "income",
]

INTEGER_ACTIONS = [
    "add", "subtract", "multiply", "floor_divide_safe", "maximum", "minimum",
    "absolute_difference", "increment_by_one", "decrement_by_one", "clamp_nonnegative",
    "clamp_upper", "clamp_lower", "modulo_safe", "square_plus",
    "choose_x_if_nonzero_else_y", "distance_plus_one",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def answer_shape(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: answer_shape(item) for key, item in value.items()}
    if isinstance(value, str):
        return "<string>"
    return "<number>"


def stable_index(*parts: object, modulo: int) -> int:
    value = hashlib.sha256("|".join(map(str, parts)).encode()).digest()
    return int.from_bytes(value[:8], "big") % modulo


def evenly_sample(frame: pd.DataFrame, count: int, offset: int) -> pd.DataFrame:
    if frame.empty:
        raise ValueError("cannot sample an empty public-data stratum")
    if len(frame) <= count:
        return frame.copy()
    positions = [round(i * (len(frame) - 1) / (count - 1)) for i in range(count)]
    shift = offset % len(frame)
    positions = sorted({(position + shift) % len(frame) for position in positions})
    cursor = 0
    while len(positions) < count:
        candidate = (shift + cursor) % len(frame)
        if candidate not in positions:
            positions.append(candidate)
        cursor += 1
    return frame.iloc[sorted(positions[:count])].copy()


def load_adult() -> pd.DataFrame:
    rows: list[list[str]] = []
    with zipfile.ZipFile(RAW / "adult.zip") as archive:
        for name in ("adult.data", "adult.test"):
            for line in archive.read(name).decode("utf-8", errors="replace").splitlines():
                if not line.strip() or line.startswith("|"):
                    continue
                values = [value.strip() for value in line.rstrip(".").split(",")]
                if len(values) == 15:
                    rows.append(values)
    frame = pd.DataFrame(rows, columns=ADULT_COLUMNS)
    for column in ("age", "education_num", "capital_gain", "capital_loss", "hours_per_week"):
        frame[column] = pd.to_numeric(frame[column])
    frame["positive"] = frame["income"].str.startswith(">50K").astype(int)
    frame["age_q"] = pd.qcut(frame["age"], 4, labels=False, duplicates="drop") + 1
    hours_raw = pd.qcut(frame["hours_per_week"], 4, labels=False, duplicates="drop")
    hour_labels = {0: 1, 1: 3, 2: 4}
    frame["hours_q"] = hours_raw.map(hour_labels)
    frame["source_index"] = range(len(frame))
    return frame


def load_beijing() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    with zipfile.ZipFile(RAW / "beijing.zip") as outer:
        nested_name = next(name for name in outer.namelist() if name.lower().endswith(".zip"))
        with zipfile.ZipFile(io.BytesIO(outer.read(nested_name))) as inner:
            for name in sorted(value for value in inner.namelist() if value.lower().endswith(".csv")):
                frames.append(pd.read_csv(io.BytesIO(inner.read(name))))
    frame = pd.concat(frames, ignore_index=True)
    frame["source_index"] = range(len(frame))
    return frame


def load_bugs() -> pd.DataFrame:
    buggy = (RAW / "bugs2fix" / "train.buggy.txt").read_text(
        encoding="utf-8", errors="replace"
    ).splitlines()
    fixed = (RAW / "bugs2fix" / "train.fixed.txt").read_text(
        encoding="utf-8", errors="replace"
    ).splitlines()
    frame = pd.DataFrame({"buggy": buggy, "fixed": fixed})
    frame["source_length"] = frame["buggy"].str.len()
    frame["patch_delta"] = (frame["fixed"].str.len() - frame["buggy"].str.len()).abs()
    frame["source_length_band"] = pd.qcut(
        frame["source_length"], 4, labels=False, duplicates="drop"
    ) + 1
    frame["patch_delta_band"] = pd.qcut(
        frame["patch_delta"], 4, labels=False, duplicates="drop"
    ) + 1
    frame["source_index"] = range(len(frame))
    return frame


def confusion(labels: list[int], predictions: list[int]) -> dict[str, int]:
    return {
        "tp": sum(y == 1 and p == 1 for y, p in zip(labels, predictions)),
        "tn": sum(y == 0 and p == 0 for y, p in zip(labels, predictions)),
        "fp": sum(y == 0 and p == 1 for y, p in zip(labels, predictions)),
        "fn": sum(y == 1 and p == 0 for y, p in zip(labels, predictions)),
    }


def f1(counts: dict[str, int]) -> float:
    denominator = 2 * counts["tp"] + counts["fp"] + counts["fn"]
    return 0.0 if denominator == 0 else 2 * counts["tp"] / denominator


def adult_case(row: dict[str, str], frame: pd.DataFrame) -> tuple[str, dict, dict]:
    context = json.loads(row["variant_context"])
    stratum = frame[
        frame["age_q"].eq(int(context["age_band"]))
        & frame["hours_q"].eq(int(context["hours_per_week_band"]))
    ]
    difficulty = int(row["adjudicated_difficulty"])
    sample = evenly_sample(
        stratum, 8 + 4 * difficulty, stable_index(row["case_id"], modulo=len(stratum))
    )
    records = [
        {
            "age": int(item.age),
            "education_num": int(item.education_num),
            "hours_per_week": int(item.hours_per_week),
            "capital_gain": int(item.capital_gain),
            "workclass": item.workclass,
            "label": int(item.positive),
        }
        for item in sample.itertuples()
    ]
    labels = [item["label"] for item in records]
    base = {
        "records": len(records),
        "positive_count": sum(labels),
        "missing_workclass_count": sum(item["workclass"] == "?" for item in records),
    }
    if difficulty >= 2:
        base.update(
            {
                "mean_age": round(statistics.fmean(item["age"] for item in records), 2),
                "mean_hours_per_week": round(
                    statistics.fmean(item["hours_per_week"] for item in records), 2
                ),
                "positive_rate": round(sum(labels) / len(labels), 4),
            }
        )
    if difficulty >= 3:
        median_age = statistics.median(item["age"] for item in records)
        median_education = statistics.median(item["education_num"] for item in records)
        median_hours = statistics.median(item["hours_per_week"] for item in records)
        pred_a = [int(item["age"] >= median_age and item["education_num"] >= median_education) for item in records]
        pred_b = [int(item["hours_per_week"] >= median_hours or item["capital_gain"] > 0) for item in records]
        counts_a, counts_b = confusion(labels, pred_a), confusion(labels, pred_b)
        f1_a, f1_b = f1(counts_a), f1(counts_b)
        selected = "A" if f1_a >= f1_b else "B"
        base.update(
            {
                "median_age": round(float(median_age), 2),
                "median_education_num": round(float(median_education), 2),
                "median_hours_per_week": round(float(median_hours), 2),
                "model_a_f1": round(f1_a, 4),
                "model_b_f1": round(f1_b, 4),
                "selected_model": selected,
                "selected_confusion": counts_a if selected == "A" else counts_b,
            }
        )
    prompt = f"""# Adult public-data microtask {row['case_id']}

Source: UCI Adult (48,842 records; CC BY 4.0). This case is a held-out
microtask for stage `{row['stage']}` at preregistered difficulty D{difficulty}.

Using only the records below, calculate every requested field. Treat `?` as
missing. Round means to 2 decimals, rates and F1 to 4 decimals. Model A predicts
positive when age >= sample median age AND education_num >= sample median.
Model B predicts positive when hours_per_week >= sample median hours OR
capital_gain > 0. F1 uses the positive class. If F1 ties, select model A.

Records:
```json
{json.dumps(records, indent=2)}
```

Return exactly one JSON object of the form:
`{{"answer": {json.dumps(answer_shape(base))}}}`
Do not include calculations outside the JSON object.
"""
    provenance = {
        "dataset": "adult",
        "dataset_sha256": "7537312dd56c2b98035880805ce99e68183a30ee468aa5329d6df0fbb3cc21bb",
        "source_indices": [int(value) for value in sample["source_index"]],
        "stratum": context["stratum"],
        "construction": "deterministic_public_row_microtask",
    }
    return prompt, {"validator_type": "numeric_json", "tolerance": 0.011, "answer": base}, provenance


def beijing_case(row: dict[str, str], frame: pd.DataFrame) -> tuple[str, dict, dict]:
    context = json.loads(row["variant_context"])
    variant = int(row["variant"])
    if variant < 12:
        station = context["stratum"].removeprefix("station_")
        stratum = frame[frame["station"].eq(station)].copy()
    else:
        quarter = variant - 12
        months = {quarter * 3 + 1, quarter * 3 + 2, quarter * 3 + 3}
        stratum = frame[frame["month"].isin(months)].copy()
    stratum = stratum.sort_values(["station", "year", "month", "day", "hour", "No"])
    difficulty = int(row["adjudicated_difficulty"])
    usable = stratum.dropna(subset=["PM2.5", "TEMP", "WSPM"])
    sample = evenly_sample(
        usable, 8 + 4 * difficulty, stable_index(row["case_id"], modulo=len(usable))
    )
    records = [
        {
            "station": str(item["station"]),
            "pm25": round(float(item["PM2.5"]), 2),
            "temperature": round(float(item["TEMP"]), 2),
            "wind_speed": round(float(item["WSPM"]), 2),
        }
        for _index, item in sample.iterrows()
    ]
    pm25 = [item["pm25"] for item in records]
    base: dict[str, Any] = {
        "records": len(records),
        "station_count": len({item["station"] for item in records}),
        "minimum_pm25": round(min(pm25), 2),
        "maximum_pm25": round(max(pm25), 2),
    }
    if difficulty >= 2:
        base.update(
            {
                "mean_pm25": round(statistics.fmean(pm25), 2),
                "median_temperature": round(statistics.median(item["temperature"] for item in records), 2),
                "maximum_wind_speed": round(max(item["wind_speed"] for item in records), 2),
            }
        )
    forecast_rows: list[dict[str, Any]] = []
    if difficulty >= 3:
        for index in range(3, len(pm25)):
            forecast_rows.append(
                {
                    "actual": pm25[index],
                    "prediction_A": pm25[index - 1],
                    "prediction_B": round(statistics.fmean(pm25[index - 3:index]), 2),
                }
            )
        mae_a = statistics.fmean(abs(item["actual"] - item["prediction_A"]) for item in forecast_rows)
        mae_b = statistics.fmean(abs(item["actual"] - item["prediction_B"]) for item in forecast_rows)
        base.update(
            {
                "model_a_mae": round(mae_a, 2),
                "model_b_mae": round(mae_b, 2),
                "selected_model": "A" if (mae_a, "A") <= (mae_b, "B") else "B",
            }
        )
    prompt = f"""# Beijing public-data microtask {row['case_id']}

Source: UCI Beijing Multi-Site Air Quality (420,768 records; CC BY 4.0).
This is a held-out `{row['stage']}` microtask at preregistered difficulty D{difficulty}.

Calculate every requested field from the records below. Round numeric results
to 2 decimals. For D3 fields, MAE is the mean absolute error over the supplied
forecast rows; lower MAE wins and ties select A.

Records:
```json
{json.dumps(records, indent=2)}
```
Forecast rows:
```json
{json.dumps(forecast_rows, indent=2)}
```

Return exactly one JSON object of the form:
`{{"answer": {json.dumps(answer_shape(base))}}}`
Do not include calculations outside the JSON object.
"""
    provenance = {
        "dataset": "beijing",
        "dataset_sha256": "b04da438b2f331ac0ffd45aebdfec0d20d2367feb5f6948c4b1f7ce1191e33c4",
        "source_indices": [int(value) for value in sample["source_index"]],
        "stratum": context["stratum"],
        "construction": "deterministic_public_row_microtask",
    }
    return prompt, {"validator_type": "numeric_json", "tolerance": 0.011, "answer": base}, provenance


def apply_action(action: str, x: int, y: int) -> int:
    if action == "add": return x + y
    if action == "subtract": return x - y
    if action == "multiply": return x * y
    if action == "floor_divide_safe": return x // y if y else 0
    if action == "maximum": return max(x, y)
    if action == "minimum": return min(x, y)
    if action == "absolute_difference": return abs(x - y)
    if action == "increment_by_one": return x + 1
    if action == "decrement_by_one": return x - 1
    if action == "clamp_nonnegative": return max(0, x)
    if action == "clamp_upper": return min(x, y)
    if action == "clamp_lower": return max(x, y)
    if action == "modulo_safe": return x % y if y else 0
    if action == "square_plus": return x * x + y
    if action == "choose_x_if_nonzero_else_y": return x if x != 0 else y
    if action == "distance_plus_one": return abs(x - y) + 1
    raise ValueError(action)


def bugs_case(row: dict[str, str], frame: pd.DataFrame) -> tuple[str, dict, dict]:
    context = json.loads(row["variant_context"])
    stratum = frame[
        frame["source_length_band"].eq(int(context["source_length_band"]))
        & frame["patch_delta_band"].eq(int(context["patch_delta_band"]))
    ]
    selected = stratum.iloc[stable_index(row["case_id"], modulo=len(stratum))]
    difficulty = int(row["adjudicated_difficulty"])
    correct = INTEGER_ACTIONS[(int(row["variant"]) + stable_index(row["case_id"], modulo=16)) % 16]
    candidate_count = {1: 4, 2: 8, 3: 16}[difficulty]
    start = INTEGER_ACTIONS.index(correct)
    candidates = [INTEGER_ACTIONS[(start + index) % 16] for index in range(candidate_count)]
    tests: list[dict[str, int]] = []
    for index in range(6):
        x = -7 + stable_index(row["case_id"], "x", index, modulo=19)
        y = -5 + stable_index(row["case_id"], "y", index, modulo=15)
        tests.append({"x": x, "y": y, "expected": apply_action(correct, x, y)})
    public_examples = tests[: 1 + difficulty]
    hidden_tests = tests[1 + difficulty :]
    if len(hidden_tests) < 2:
        hidden_tests = tests[-2:]
    prompt = f"""# Bugs2Fix-stratified executable surrogate {row['case_id']}

Source stratum: CodeXGLUE Bugs2Fix-small (46,680 normalized Java method
pairs; C-UDA). The source pair below establishes corpus provenance, but it is
not directly compilable because identifiers are normalized. Therefore this
case is explicitly a behavioral repair surrogate, not a repository-level Java
repair claim.

Source buggy method:
`{selected['buggy']}`

Source fixed method:
`{selected['fixed']}`

Select the single `repair_action` that satisfies the behavioral specification
shown by the public examples. Candidate actions:
`{json.dumps(candidates)}`

Public examples:
```json
{json.dumps(public_examples, indent=2)}
```

The validator will execute the selected action on additional hidden integer
inputs. Return exactly:
`{{"answer": {{"repair_action": "one_candidate_action"}}}}`
"""
    expected = {
        "validator_type": "behavioral_integer_repair",
        "answer": {"repair_action": correct},
        "hidden_tests": hidden_tests,
    }
    provenance = {
        "dataset": "bugs2fix-small",
        "buggy_sha256": "dfb4366dedb73dd40f78c3af870ccb0a1aeff2d9ceb45585df26c99897740748",
        "fixed_sha256": "c98b1139265d33e787a9dd742a464e7eb5bd137ebb3fcb54f0416ee7672739f3",
        "source_index": int(selected["source_index"]),
        "stratum": context["stratum"],
        "construction": "executable_behavioral_surrogate",
        "claim_boundary": "not_repository_level_program_repair",
    }
    return prompt, expected, provenance


def main() -> int:
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    if len(rows) != 60:
        raise ValueError("expected 60 selected cases")
    adult, beijing, bugs = load_adult(), load_beijing(), load_bugs()
    if BUNDLES.exists():
        shutil.rmtree(BUNDLES)
    BUNDLES.mkdir(parents=True)
    lock_cases: list[dict[str, Any]] = []
    for row in rows:
        if row["workload"] == "adult_ml":
            prompt, expected, provenance = adult_case(row, adult)
        elif row["workload"] == "beijing_ml":
            prompt, expected, provenance = beijing_case(row, beijing)
        else:
            prompt, expected, provenance = bugs_case(row, bugs)
        destination = BUNDLES / row["case_id"]
        destination.mkdir()
        (destination / "prompt.md").write_text(prompt, encoding="utf-8")
        (destination / "expected.json").write_text(
            json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (destination / "provenance.json").write_text(
            json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        shutil.copy2(VALIDATOR_SOURCE, destination / "validator.py")
        row["execution_bundle"] = f"case_bundles/{row['case_id']}"
        row["validator_command"] = "python validator.py --candidate {candidate}"
        row["executable_ready"] = "True"
        lock_cases.append(
            {
                "case_id": row["case_id"],
                "workload": row["workload"],
                "difficulty": int(row["adjudicated_difficulty"]),
                "files": {
                    name: sha256(destination / name)
                    for name in ("prompt.md", "expected.json", "provenance.json", "validator.py")
                },
            }
        )
    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    lock = {
        "schema_version": "1.0",
        "status": "MATERIALIZED_NOT_FROZEN",
        "research_results": False,
        "case_count": len(lock_cases),
        "source_manifest": "case_manifest.csv",
        "validator_template_sha256": sha256(VALIDATOR_SOURCE),
        "cases": lock_cases,
    }
    (HERE / "case_bundle_lock.json").write_text(
        json.dumps(lock, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": lock["status"], "cases": len(lock_cases)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
