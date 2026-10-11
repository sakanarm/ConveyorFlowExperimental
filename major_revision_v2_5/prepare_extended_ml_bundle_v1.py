"""Materialize public-only Bank/Covertype ML DAG bundles for v2.5.

This preparation makes no provider calls and cannot be used as an allocation
result. Hidden labels remain outside every candidate-visible bundle.
"""

from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import audit_bank_gate_v1
import audit_covertype_gate_v1


HERE = Path(__file__).resolve().parent
DATA = HERE / "new_ml_corpora_v1"
LOCK = HERE / "extended_ml_bundle_lock_v1.json"
ROOT = HERE / "results/v25_ml_integration_v1"
CASES = {"V25_BANK_01": "bank", "V25_COVERTYPE_01": "covertype"}
FILES = ("train.csv", "validation.csv", "test_features.csv")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def stable_lock() -> dict:
    bank, covertype = audit_bank_gate_v1.audit(), audit_covertype_gate_v1.audit()
    if (bank["status"] != "bank_reference_gate_audited_not_paid_experiment" or
            covertype["status"] != "covertype_reference_gate_audited_not_paid_experiment"):
        raise ValueError("Public ML source/reference gates not audited")
    split = read(DATA / "split_manifest.json")
    hashes = {}
    for case_id, corpus in CASES.items():
        item = split["corpora"][corpus]
        paths = {}
        for name in FILES:
            stem = name.removesuffix(".csv")
            source = DATA / "public" / corpus / name
            if (source.is_symlink() or not source.is_file() or
                    sha256(source) != item["sha256"][stem]):
                raise ValueError("Public ML input hash mismatch: " + corpus + "/" + name)
            paths[name] = sha256(source)
        hashes[case_id] = paths
    return {
        "status": "v2_5_extended_ml_public_bundle_frozen_before_provider",
        "research_results": False, "provider_calls": 0,
        "case_corpus": CASES,
        "source_manifest_sha256": sha256(DATA / "source_manifest.json"),
        "split_manifest_sha256": sha256(DATA / "split_manifest.json"),
        "quality_gate_sha256": {
            "bank": sha256(DATA / "bank_quality_gate_v1.json"),
            "covertype": sha256(DATA / "covertype_quality_gate_v1.json"),
        },
        "public_input_sha256": hashes,
        "runner_sha256": sha256(Path(__file__)),
        "candidate_visible_files": ["bundle_manifest.json", "input/train.csv",
                                    "input/validation.csv", "input/test_features.csv"],
        "hidden_labels_included": False,
    }


def freeze() -> dict:
    stable = stable_lock()
    if LOCK.exists():
        locked = read(LOCK)
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError("Extended ML bundle lock drift")
        return locked
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def materialize(case_id: str) -> dict:
    lock = freeze()
    if case_id not in CASES:
        raise ValueError("Case outside frozen ML extension")
    corpus = CASES[case_id]
    target = ROOT / case_id
    if target.exists():
        raise FileExistsError("Public bundle already exists; do not overwrite")
    public = DATA / "public" / corpus
    target.mkdir(parents=True)
    for directory in ("input", "submission", "dag_output", "main_generation"):
        (target / directory).mkdir()
    for name in FILES:
        source = public / name
        destination = target / "input" / name
        shutil.copyfile(source, destination)
        if sha256(destination) != lock["public_input_sha256"][case_id][name]:
            raise ValueError("Copied public ML input changed")
    split = read(DATA / "split_manifest.json")["corpora"][corpus]
    manifest = {
        "case_id": case_id, "corpus": corpus,
        "task_type": "binary_classification" if corpus == "bank" else
                     "seven_class_classification",
        "metric": "roc_auc" if corpus == "bank" else "macro_f1",
        "hidden_labels_included": False,
        "excluded_features": ["duration"] if corpus == "bank" else [],
        "public_input_sha256": lock["public_input_sha256"][case_id],
        "quality_gate_sha256": lock["quality_gate_sha256"][corpus],
        "split_manifest_sha256": lock["split_manifest_sha256"],
        "rows": split["rows"],
        "provider_calls": 0,
    }
    save_new(target / "bundle_manifest.json", manifest)
    origin = {"case_id": case_id, "corpus": corpus,
              "bundle_lock_sha256": sha256(LOCK),
              "bundle_manifest_sha256": sha256(target / "bundle_manifest.json"),
              "public_only_no_trusted_predecessor": True,
              "not_allocation_or_llm_result": True}
    save_new(target / "main_bundle_origin.json", origin)
    return {"status": "public_bundle_materialized_not_research_result",
            "case_id": case_id, "corpus": corpus,
            "bundle_manifest_sha256": sha256(target / "bundle_manifest.json"),
            "public_files": list(FILES), "provider_calls": 0}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--freeze", action="store_true")
    cli.add_argument("--materialize", choices=tuple(CASES))
    args = cli.parse_args()
    if args.freeze == bool(args.materialize):
        cli.error("Choose exactly one action")
    print(json.dumps({"status": freeze()["status"], "provider_calls": 0}
                     if args.freeze else materialize(args.materialize), sort_keys=True))
