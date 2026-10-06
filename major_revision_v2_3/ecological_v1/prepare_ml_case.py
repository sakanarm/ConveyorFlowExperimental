"""Materialize a new specification and an investigator-only numeric reference gate.

Only trusted NumPy reference code runs on the host. No candidate Python/joblib
is imported, executed or deserialized. Container preflight is a separate gate.
"""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from prepare_design import audit, DEST, HERE, MAJOR, sha256


def filter_csv(source, destination, excluded, *, development):
    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if "row_id" not in fields or ("target" in fields) != development:
            raise ValueError("Development/test target separation failed")
        if not set(excluded).issubset(fields) or {"row_id", "target"} & set(excluded):
            raise ValueError("Invalid feature exclusion")
        public_fields = [f for f in fields if f not in excluded]
        with destination.open("x", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=public_fields)
            writer.writeheader()
            count = 0
            for row in reader:
                if None in row:
                    raise ValueError("Malformed source CSV row")
                writer.writerow({f: row[f] for f in public_fields})
                count += 1
    return count


def prepare(case_id):
    verified_design = audit()
    design = json.loads((DEST / "design.json").read_text(encoding="utf-8"))
    case = next((c for c in design["ml_specifications"] if c["case_id"] == case_id), None)
    if case is None:
        raise ValueError("Case is not in the outcome-blind preparation pool")
    corpus = case["corpus"]
    original = json.loads((MAJOR / "ml_cases/case_manifest.json").read_text(encoding="utf-8"))
    data = original["corpora"][corpus]
    source = MAJOR / "ml_cases/data" / corpus
    label_path = MAJOR / "ml_cases/hidden" / corpus / "test_labels.csv"
    for name in ("train", "validation", "test_features"):
        if sha256(source / (name + ".csv")) != data["sha256"][name]:
            raise ValueError("Original public input changed")
    if sha256(label_path) != data["sha256"]["test_labels"]:
        raise ValueError("Original verifier labels changed")
    root = HERE / "ml_preparation" / case_id
    if root.exists():
        raise FileExistsError("Preserve existing preparation; never overwrite it")
    public, verifier = root / "public", root / "verifier"
    (public / "input").mkdir(parents=True)
    (public / "submission").mkdir()
    verifier.mkdir()
    started = {"case_id": case_id, "status": "preparation_started_no_provider_calls",
               "created_at_utc": datetime.now(timezone.utc).isoformat(),
               "design_sha256": verified_design["design_sha256"], "no_provider_calls": True}
    (root / "started.json").write_text(json.dumps(started, indent=2) + "\n", encoding="utf-8")
    counts, hashes = {}, {}
    for name in ("train", "validation", "test_features"):
        target = public / "input" / (name + ".csv")
        counts[name] = filter_csv(source / (name + ".csv"), target, case["excluded_features"], development=name != "test_features")
        expected_rows = data["rows"]["test" if name == "test_features" else name]
        if counts[name] != expected_rows:
            raise ValueError("Public row accounting differs from original manifest")
        hashes[name] = sha256(target)
    if counts["train"] < case["minimum_train_rows"]:
        raise ValueError("Training population below the registered 20,000-row requirement")
    bundle = {"status": "new_public_task_specification_not_candidate_result", "case_id": case_id,
              "corpus": corpus, "excluded_features": case["excluded_features"],
              "design_sha256": verified_design["design_sha256"], "public_input_sha256": hashes,
              "hidden_labels_included": False, "source_rows_reused": True, "split": case["split"]}
    (public / "bundle_manifest.json").write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    if str(MAJOR) not in sys.path:
        sys.path.insert(0, str(MAJOR))
    from reference_ml_gates import evaluate_case
    evidence, predictions = evaluate_case(case)  # Trusted numeric reference, not model-generated code.
    prediction_path = verifier / "trusted_reference_predictions.csv"
    with prediction_path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["row_id", "prediction"])
        writer.writeheader()
        writer.writerows(predictions)
    gate = {"status": "numeric_reference_gate_prepared_before_provider_calls", "case_id": case_id,
            "corpus": corpus, "excluded_features": case["excluded_features"], **evidence,
            "design_sha256": verified_design["design_sha256"],
            "hidden_labels_sha256": data["sha256"]["test_labels"],
            "reference_predictions_sha256": sha256(prediction_path),
            "reference_script_sha256": sha256(MAJOR / "reference_ml_gates.py"),
            "preparation_script_sha256": sha256(Path(__file__)),
            "no_provider_calls": True, "not_an_llm_observation": True,
            "container_reference_stages_verified": False}
    gate_path = verifier / "quality_gate.json"
    gate_path.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    result = {"status": "public_inputs_and_numeric_reference_prepared_not_live_ready",
              "case_id": case_id, "rows": counts, "public_input_sha256": hashes,
              "quality_gate_sha256": sha256(gate_path), "no_provider_calls": True,
              "not_an_llm_observation": True, "trusted_container_preflight_pending": True,
              "paid_execution_allowed": False, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    (root / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.case_id)))
