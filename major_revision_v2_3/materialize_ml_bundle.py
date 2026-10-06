"""Create one public-only end-to-end ML candidate bundle using stdlib CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
CASES = HERE / "ml_cases"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def materialize(case_id: str, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite candidate bundle: {output}")
    manifest_path = CASES / "case_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    case = next((item for item in manifest["variants"] if item["case_id"] == case_id), None)
    if case is None:
        raise ValueError(f"unknown case {case_id}")
    corpus = case["corpus"]
    source = CASES / "data" / corpus
    expected_hashes = manifest["corpora"][corpus]["sha256"]
    for name in ("train", "validation", "test_features"):
        if sha256(source / f"{name}.csv") != expected_hashes[name]:
            raise ValueError(f"frozen {corpus} {name} input changed")
    output.mkdir(parents=True)
    public = output / "input"
    public.mkdir()
    excluded = set(case["excluded_features"])
    filtered_hashes = {}
    for name in ("train", "validation", "test_features"):
        src_path = source / f"{name}.csv"
        dst_path = public / f"{name}.csv"
        with src_path.open("r", encoding="utf-8", newline="") as src, dst_path.open(
            "w", encoding="utf-8", newline=""
        ) as dst:
            reader = csv.DictReader(src)
            if not excluded.issubset(reader.fieldnames or []):
                raise AssertionError("excluded feature absent from source")
            fields = [column for column in reader.fieldnames or [] if column not in excluded]
            if name == "test_features" and "target" in fields:
                raise AssertionError("hidden test target leaked into public bundle")
            if name != "test_features" and "target" not in fields:
                raise AssertionError("development target missing")
            writer = csv.DictWriter(dst, fieldnames=fields)
            writer.writeheader()
            for row in reader:
                writer.writerow({field: row[field] for field in fields})
        filtered_hashes[name] = sha256(dst_path)
    task = (
        f"Case {case_id}: build a complete, executable {corpus} ML pipeline.\n"
        "Only input/train.csv, input/validation.csv and input/test_features.csv "
        "are available. Never read external data or use the network.\n"
        "Write submission/train_model.py and submission/predict.py. The first "
        "must accept --train, --validation and --output-model, train only on "
        "the supplied development data, and save output/model.joblib. The "
        "second must accept --model, --test and --output-predictions, load the "
        "saved model in a fresh process, and write output/predictions.csv with "
        "exactly row_id,prediction columns and "
        "one row per test_features.csv row. Adult predictions are positive-class "
        "probabilities in [0,1]; Beijing predictions are numeric PM2.5 estimates.\n"
        "Fit preprocessing on training data only. Validation may guide model "
        "selection, but hidden test labels are never available. A clean "
        "container will run the pipeline from scratch with no network.\n"
        f"Excluded features: {', '.join(sorted(excluded)) if excluded else 'none'}.\n"
    )
    (output / "TASK.txt").write_text(task, encoding="utf-8")
    (output / "submission").mkdir()
    info = {
        "status": "public_only_candidate_bundle",
        "case_id": case_id,
        "corpus": corpus,
        "excluded_features": sorted(excluded),
        "source_case_manifest_sha256": sha256(manifest_path),
        "public_input_sha256": filtered_hashes,
        "hidden_labels_included": False,
    }
    (output / "bundle_manifest.json").write_text(
        json.dumps(info, indent=2) + "\n", encoding="utf-8"
    )
    return info


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize(args.case_id, args.output), indent=2))


if __name__ == "__main__":
    main()
