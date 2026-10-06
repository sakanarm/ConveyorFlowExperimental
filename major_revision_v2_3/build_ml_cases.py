"""Prepare leakage-controlled Adult and Beijing pipeline inputs with stdlib.

Hidden labels are written outside the public bundle tree. Never mount the
hidden directory or original source ZIPs into a candidate execution sandbox.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import random
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
CASES = HERE / "ml_cases"
PUBLIC = CASES / "data"
HIDDEN = CASES / "hidden"
ADULT_COLUMNS = [
    "age", "workclass", "fnlwgt", "education", "education_num",
    "marital_status", "occupation", "relationship", "race", "sex",
    "capital_gain", "capital_loss", "hours_per_week", "native_country", "target",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def source_manifest() -> dict:
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
    sources = {item["id"]: item for item in manifest["datasets"]}
    for name in ("adult", "beijing"):
        item = sources[name]
        path = ROOT / item["local_path"]
        if not path.is_file() or sha256(path) != item["sha256"]:
            raise ValueError(f"frozen {name} source ZIP is missing or changed")
    return sources


def paths(name: str) -> dict[str, Path]:
    public_dir = PUBLIC / name
    hidden_dir = HIDDEN / name
    public_dir.mkdir(parents=True, exist_ok=True)
    hidden_dir.mkdir(parents=True, exist_ok=True)
    return {
        "train": public_dir / "train.csv",
        "validation": public_dir / "validation.csv",
        "test_features": public_dir / "test_features.csv",
        "test_labels": hidden_dir / "test_labels.csv",
    }


def adult_rows(blob: bytes, prefix: str) -> list[list[str]]:
    result = []
    for raw in csv.reader(io.StringIO(blob.decode("utf-8"))):
        if not raw or raw[0].startswith("|"):
            continue
        if len(raw) != len(ADULT_COLUMNS):
            raise AssertionError(f"unexpected Adult row width: {len(raw)}")
        fields = [value.strip() if value.strip() != "?" else "" for value in raw]
        label = fields[-1].rstrip(".")
        if label not in {"<=50K", ">50K"}:
            raise AssertionError(f"unexpected Adult label: {label}")
        fields[-1] = "1" if label == ">50K" else "0"
        result.append([f"{prefix}_{len(result):05d}", *fields])
    return result


def build_adult() -> dict:
    with zipfile.ZipFile(ROOT / "data" / "raw" / "adult.zip") as archive:
        development = adult_rows(archive.read("adult.data"), "adult_train")
        test = adult_rows(archive.read("adult.test"), "adult_test")
    if len(development) + len(test) != 48_842:
        raise AssertionError("Adult source row count changed")
    rng = random.Random(20261003)
    validation_ids = set()
    for label in ("0", "1"):
        ids = [index for index, row in enumerate(development) if row[-1] == label]
        rng.shuffle(ids)
        validation_ids.update(ids[:round(0.20 * len(ids))])
    train = [row for index, row in enumerate(development) if index not in validation_ids]
    validation = [row for index, row in enumerate(development) if index in validation_ids]
    output = paths("adult")
    header = ["row_id", *ADULT_COLUMNS]
    for key, rows in (("train", train), ("validation", validation)):
        with output[key].open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)
    with output["test_features"].open("w", encoding="utf-8", newline="") as public, output[
        "test_labels"
    ].open("w", encoding="utf-8", newline="") as hidden:
        features, labels = csv.writer(public), csv.writer(hidden)
        features.writerow(header[:-1])
        labels.writerow(["row_id", "target"])
        for row in test:
            features.writerow(row[:-1])
            labels.writerow([row[0], row[-1]])
    return {
        "task": "binary_classification",
        "metric": "roc_auc",
        "rows": {"train": len(train), "validation": len(validation), "test": len(test)},
        "features": ADULT_COLUMNS[:-1],
        "paths": {key: str(path.relative_to(HERE)) for key, path in output.items()},
        "sha256": {key: sha256(path) for key, path in output.items()},
    }


def beijing_zip() -> zipfile.ZipFile:
    with zipfile.ZipFile(ROOT / "data" / "raw" / "beijing.zip") as outer:
        nested = outer.read("PRSA2017_Data_20130301-20170228.zip")
    return zipfile.ZipFile(io.BytesIO(nested))


def build_beijing() -> dict:
    output = paths("beijing")
    counts = {"train": 0, "validation": 0, "test": 0}
    missing_target = 0
    raw_count = 0
    with beijing_zip() as archive:
        members = sorted(name for name in archive.namelist() if name.lower().endswith(".csv"))
        if len(members) != 12:
            raise AssertionError("expected 12 Beijing station CSV files")
        with archive.open(members[0]) as source:
            reader = csv.DictReader(io.TextIOWrapper(source, encoding="utf-8-sig"))
            times = sorted({
                f"{int(row['year']):04d}-{int(row['month']):02d}-{int(row['day']):02d} "
                f"{int(row['hour']):02d}:00:00"
                for row in reader
            })
        cut1, cut2 = times[int(len(times) * 0.70)], times[int(len(times) * 0.85)]
        with output["train"].open("w", encoding="utf-8", newline="") as train_handle, output[
            "validation"
        ].open("w", encoding="utf-8", newline="") as val_handle, output[
            "test_features"
        ].open("w", encoding="utf-8", newline="") as test_handle, output[
            "test_labels"
        ].open("w", encoding="utf-8", newline="") as hidden_handle:
            writers = {
                "train": csv.writer(train_handle),
                "validation": csv.writer(val_handle),
                "test_features": csv.writer(test_handle),
                "test_labels": csv.writer(hidden_handle),
            }
            feature_names = None
            for member in members:
                with archive.open(member) as source:
                    reader = csv.DictReader(io.TextIOWrapper(source, encoding="utf-8-sig"))
                    if feature_names is None:
                        feature_names = [
                            name for name in reader.fieldnames or [] if name not in {"No", "PM2.5"}
                        ] + ["timestamp"]
                        full_header = ["row_id", *feature_names, "target"]
                        writers["train"].writerow(full_header)
                        writers["validation"].writerow(full_header)
                        writers["test_features"].writerow(full_header[:-1])
                        writers["test_labels"].writerow(["row_id", "target"])
                    elif set(reader.fieldnames or []) != set(feature_names) - {"timestamp"} | {"No", "PM2.5"}:
                        raise AssertionError("Beijing station schemas differ")
                    for row in reader:
                        row_id = f"beijing_{raw_count:06d}"
                        raw_count += 1
                        target = row["PM2.5"].strip()
                        if target.upper() in {"", "NA", "NAN", "NULL"}:
                            missing_target += 1
                            continue
                        stamp = (
                            f"{int(row['year']):04d}-{int(row['month']):02d}-{int(row['day']):02d} "
                            f"{int(row['hour']):02d}:00:00"
                        )
                        fields = [row_id, *(row[name].strip() for name in feature_names if name != "timestamp"), stamp]
                        if stamp < cut1:
                            writers["train"].writerow([*fields, target])
                            counts["train"] += 1
                        elif stamp < cut2:
                            writers["validation"].writerow([*fields, target])
                            counts["validation"] += 1
                        else:
                            writers["test_features"].writerow(fields)
                            writers["test_labels"].writerow([row_id, target])
                            counts["test"] += 1
    if raw_count != 420_768 or min(counts.values()) < 20_000:
        raise AssertionError(f"Beijing row counts invalid: raw={raw_count}, splits={counts}")
    return {
        "task": "regression",
        "metric": "mean_absolute_error",
        "rows": counts,
        "raw_rows": raw_count,
        "missing_target_rows_excluded": missing_target,
        "chronological_cutoffs": {"validation_start": cut1, "test_start": cut2},
        "features": feature_names,
        "paths": {key: str(path.relative_to(HERE)) for key, path in output.items()},
        "sha256": {key: sha256(path) for key, path in output.items()},
    }


def main() -> None:
    source = source_manifest()
    adult = build_adult()
    print(f"adult_rows={adult['rows']}", flush=True)
    beijing = build_beijing()
    print(f"beijing_rows={beijing['rows']}", flush=True)
    variants = [
        {"case_id": "ADULT_P0", "corpus": "adult", "excluded_features": [], "status": "pilot_only"},
        {"case_id": "ADULT_P1", "corpus": "adult", "excluded_features": ["fnlwgt"], "status": "pilot_only"},
        {"case_id": "ADULT_P2", "corpus": "adult", "excluded_features": ["education_num"], "status": "pilot_only"},
        {"case_id": "ADULT_P3", "corpus": "adult", "excluded_features": ["occupation", "native_country"], "status": "pilot_only"},
        {"case_id": "BEIJING_P0", "corpus": "beijing", "excluded_features": [], "status": "pilot_only"},
        {"case_id": "BEIJING_P1", "corpus": "beijing", "excluded_features": ["PM10"], "status": "pilot_only"},
        {"case_id": "BEIJING_P2", "corpus": "beijing", "excluded_features": ["PM10", "NO2"], "status": "pilot_only"},
        {"case_id": "BEIJING_P3", "corpus": "beijing", "excluded_features": ["PM10", "SO2", "NO2", "CO", "O3"], "status": "pilot_only"},
    ]
    manifest = {
        "status": "pilot_inputs_prepared_not_executed",
        "research_results": False,
        "source_sha256": {name: source[name]["sha256"] for name in ("adult", "beijing")},
        "split_rule": "Adult official test plus stratified 80/20 development split; Beijing chronological 70/15/15 unique-time split",
        "corpora": {"adult": adult, "beijing": beijing},
        "variants": variants,
        "candidate_container_mount": "only case-specific public inputs; never hidden labels or data/raw",
    }
    path = CASES / "case_manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"case_manifest={path} sha256={sha256(path)} variants={len(variants)}")


if __name__ == "__main__":
    main()
