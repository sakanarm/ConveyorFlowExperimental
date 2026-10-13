"""Independent row-level audit of the two new source-derived ML splits."""

from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent / "new_ml_corpora_v1"
MANIFEST = ROOT / "split_manifest.json"


def inspect(name: str, frozen: dict) -> dict:
    paths = {key: ROOT / rel for key, rel in frozen["paths"].items()}
    by_split = {}
    feature_signatures = {}
    for split, filename in (("train", paths["train"]),
                            ("validation", paths["validation"]),
                            ("test", paths["test_features"])):
        ids, features, labels = set(), set(), Counter()
        with filename.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            fields = list(reader.fieldnames or [])
            expected = ["row_id", *frozen["features"]] + ([] if split == "test" else ["target"])
            if fields != expected or "duration" in fields:
                raise ValueError(f"{name}/{split}: public input schema mismatch or leakage")
            for row in reader:
                row_id = row["row_id"]
                if row_id in ids or not row_id.startswith(name + "_"):
                    raise ValueError(f"{name}/{split}: duplicate or invalid row ID")
                ids.add(row_id)
                key = "\x1f".join(row[col] for col in frozen["features"]).encode("utf-8")
                features.add(hashlib.blake2b(key, digest_size=16).digest())
                if split != "test":
                    labels[row["target"]] += 1
        if len(ids) != frozen["rows"][split]:
            raise ValueError(f"{name}/{split}: wrong row count")
        by_split[split] = {"ids": ids, "labels": labels}
        feature_signatures[split] = features
    with paths["test_labels"].open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["row_id", "target"]:
            raise ValueError(f"{name}: hidden label schema mismatch")
        hidden = list(reader)
    if {row["row_id"] for row in hidden} != by_split["test"]["ids"] or len(hidden) != len(by_split["test"]["ids"]):
        raise ValueError(f"{name}: hidden test labels not aligned")
    by_split["test"]["labels"] = Counter(row["target"] for row in hidden)
    if any(by_split[left]["ids"] & by_split[right]["ids"]
           for left, right in (("train", "validation"), ("train", "test"), ("validation", "test"))):
        raise ValueError(f"{name}: row IDs overlap across splits")
    duplicate_groups = {f"{left}_{right}": len(feature_signatures[left] & feature_signatures[right])
                        for left, right in (("train", "validation"), ("train", "test"), ("validation", "test"))}
    if name == "covertype" and any(duplicate_groups.values()):
        raise ValueError("Covertype exact feature groups crossed a split boundary")
    for split in by_split:
        if dict(by_split[split]["labels"]) != frozen["class_counts"][split]:
            raise ValueError(f"{name}/{split}: frozen class counts mismatch")
    return {"rows": {split: len(by_split[split]["ids"]) for split in by_split},
            "class_counts": {split: dict(by_split[split]["labels"]) for split in by_split},
            "cross_split_exact_feature_group_counts": duplicate_groups,
            "hidden_test_labels_aligned": True,
            "public_input_omits_bank_duration": name != "bank" or "duration" not in frozen["features"]}


def main() -> None:
    frozen = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = {name: inspect(name, info) for name, info in frozen["corpora"].items()}
    print(json.dumps({"status": "row_level_split_audit_passed_not_llm_qualified",
                      "provider_calls": 0, "corpora": result}, sort_keys=True))


if __name__ == "__main__":
    main()
