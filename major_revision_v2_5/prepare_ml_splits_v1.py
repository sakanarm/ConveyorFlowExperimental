"""Prepare leakage-aware public ML inputs and separate hidden labels.

Bank uses the source's date-ordered row sequence and omits post-call duration.
Covertype has no timestamp: exact feature-identical rows are assigned to the
same deterministic split. These are corpus-level units, not new independent
corpora and not yet qualified LLM experiment cases.
"""

from __future__ import annotations

from collections import Counter
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import zipfile

import acquire_ml_sources_v1 as source


HERE = Path(__file__).resolve().parent
ROOT = HERE / "new_ml_corpora_v1"
PUBLIC = ROOT / "public"
HIDDEN = ROOT / "hidden"
MANIFEST = ROOT / "split_manifest.json"
SEED = "ConveyorFlow-v2.5-ml-split-20261011"
CV_NUMERIC = ["Elevation", "Aspect", "Slope", "Horizontal_Distance_To_Hydrology",
              "Vertical_Distance_To_Hydrology", "Horizontal_Distance_To_Roadways",
              "Hillshade_9am", "Hillshade_Noon", "Hillshade_3pm",
              "Horizontal_Distance_To_Fire_Points"]
CV_FEATURES = CV_NUMERIC + [f"Wilderness_Area_{n}" for n in range(1, 5)] + [
    f"Soil_Type_{n}" for n in range(1, 41)]


def paths(name: str) -> dict[str, Path]:
    return {"train": PUBLIC / name / "train.csv",
            "validation": PUBLIC / name / "validation.csv",
            "test_features": PUBLIC / name / "test_features.csv",
            "test_labels": HIDDEN / name / "test_labels.csv"}


def write_bundle(name: str, fieldnames: list[str], rows, split_rule: str,
                 expected: int, min_train: int = 20_000) -> dict:
    outputs = paths(name)
    for path in outputs.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError(f"split output already exists: {path}")
    counts = Counter()
    classes = {key: Counter() for key in ("train", "validation", "test")}
    with (outputs["train"].open("x", encoding="utf-8", newline="") as tr,
          outputs["validation"].open("x", encoding="utf-8", newline="") as va,
          outputs["test_features"].open("x", encoding="utf-8", newline="") as te,
          outputs["test_labels"].open("x", encoding="utf-8", newline="") as label):
        writers = {"train": csv.writer(tr), "validation": csv.writer(va),
                   "test_features": csv.writer(te), "test_labels": csv.writer(label)}
        full_header = ["row_id", *fieldnames, "target"]
        writers["train"].writerow(full_header)
        writers["validation"].writerow(full_header)
        writers["test_features"].writerow(full_header[:-1])
        writers["test_labels"].writerow(["row_id", "target"])
        for split, row_id, features, target in rows:
            if split not in classes or len(features) != len(fieldnames):
                raise ValueError(f"{name}: invalid row or split")
            counts[split] += 1
            classes[split][target] += 1
            if split == "test":
                writers["test_features"].writerow([row_id, *features])
                writers["test_labels"].writerow([row_id, target])
            else:
                writers[split].writerow([row_id, *features, target])
    if sum(counts.values()) != expected or counts["train"] < min_train or min(counts.values()) == 0:
        raise ValueError(f"{name}: invalid split counts {counts}")
    return {"rows": dict(counts), "class_counts": {k: dict(v) for k, v in classes.items()},
            "features": fieldnames, "split_rule": split_rule,
            "paths": {k: v.relative_to(ROOT).as_posix() for k, v in outputs.items()},
            "sha256": {k: source.sha256(v) for k, v in outputs.items()}}


def bank_rows():
    with zipfile.ZipFile(ROOT / "raw/bank.zip") as outer:
        with zipfile.ZipFile(io.BytesIO(outer.read("bank.zip"))) as inner:
            name = next((n for n in inner.namelist() if n.endswith("bank-full.csv")), None)
            if name is None:
                raise ValueError("bank-full.csv absent")
            with inner.open(name) as binary:
                reader = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8"), delimiter=";")
                columns = list(reader.fieldnames or [])
                if len(columns) != 17 or "duration" not in columns or columns[-1] != "y":
                    raise ValueError("unexpected Bank schema")
                features = [col for col in columns if col not in ("duration", "y")]
                seen = {"train": set(), "validation": set(), "test": set()}
                overlap = Counter()
                def generator():
                    for index, record in enumerate(reader):
                        split = "train" if index < 31_647 else "validation" if index < 38_429 else "test"
                        values = [record[col] for col in features]
                        target = record["y"]
                        if target not in ("yes", "no"):
                            raise ValueError("unexpected Bank target")
                        signature = tuple(values)
                        for other in seen:
                            if other != split and signature in seen[other]:
                                overlap[f"{other}/{split}"] += 1
                        seen[split].add(signature)
                        yield split, f"bank_{index:06d}", values, "1" if target == "yes" else "0"
                result = write_bundle("bank", features, generator(),
                    "Source bank-full.csv order (UCI says ordered by date); first 70%, next 15%, last 15%; no shuffle; drop post-call duration before writing any public input",
                    expected=45_211)
                result["exact_feature_duplicate_cross_split_rows"] = dict(overlap)
                result["client_group_split_verified"] = False
                result["interpretation_note"] = "No client identifier or exact contact timestamp; temporal order is source row order and client-level independence cannot be established."
                return result


def covertype_rows():
    with zipfile.ZipFile(ROOT / "raw/covertype.zip") as outer:
        with outer.open("covtype.data.gz") as packed:
            with gzip.GzipFile(fileobj=packed) as unpacked:
                reader = csv.reader(io.TextIOWrapper(unpacked, encoding="ascii"))
                def generator():
                    for index, values in enumerate(reader):
                        if len(values) != 55 or values[-1] not in "1234567" or len(values[-1]) != 1:
                            raise ValueError("unexpected Covertype schema/target")
                        features = values[:-1]
                        # Identical full feature vectors, even with conflicting labels,
                        # remain in the same split. No target participates in hashing.
                        key = (SEED + "|" + ",".join(features)).encode("ascii")
                        bucket = int.from_bytes(hashlib.blake2b(key, digest_size=8).digest(), "big") / 2**64
                        split = "train" if bucket < .70 else "validation" if bucket < .85 else "test"
                        yield split, f"covertype_{index:06d}", features, values[-1]
                return write_bundle("covertype", CV_FEATURES, generator(),
                    "Deterministic 70/15/15 blake2b grouping on all 54 features (not label); exact feature-identical rows cannot cross splits",
                    expected=581_012)


def audit() -> dict:
    source.audit()
    frozen = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (frozen["status"] != "splits_prepared_not_verifier_qualified" or
            frozen["source_manifest_sha256"] != source.sha256(source.MANIFEST) or
            frozen["runner_sha256"] != source.sha256(Path(__file__)) or
            frozen["provider_calls"] != 0):
        raise ValueError("split protocol identity drift")
    for name, info in frozen["corpora"].items():
        for key, relpath in info["paths"].items():
            if source.sha256(ROOT / relpath) != info["sha256"][key]:
                raise ValueError(f"{name}/{key}: split file changed")
    return {"status": "split_identity_verified_not_verifier_qualified",
            "corpora": len(frozen["corpora"]), "rows": {k: v["rows"] for k, v in frozen["corpora"].items()},
            "provider_calls": 0, "manifest_sha256": source.sha256(MANIFEST)}


def prepare() -> dict:
    source.audit()
    if MANIFEST.exists():
        return audit()
    if PUBLIC.exists() or HIDDEN.exists():
        raise FileExistsError("partial split directory retained for inspection")
    datasets = {"bank": bank_rows(), "covertype": covertype_rows()}
    manifest = {"status": "splits_prepared_not_verifier_qualified",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_manifest_sha256": source.sha256(source.MANIFEST),
                "runner_sha256": source.sha256(Path(__file__)),
                "split_seed": SEED, "corpora": datasets,
                "provider_calls": 0, "paid_execution_allowed": False,
                "note": "Reference quality gates and live-LLM case integration must be frozen and audited separately."}
    with MANIFEST.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return audit()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    print(json.dumps(audit() if args.audit else prepare(), sort_keys=True))
