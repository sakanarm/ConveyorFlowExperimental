"""Prepare outcome-blind, disjoint task-specification pools; no API/container calls.

This is an investigator-only preparation capsule, NOT an execution-ready lock.
All source corpora are reused. New feature-subset specifications are not new
independent datasets and are not claimed to be absent from model pretraining.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import shlex
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
MAJOR = HERE.parent
V2 = MAJOR.parent
DEST = HERE / "prepared_design"
PROJECTS = ("luigi", "matplotlib", "pandas")
STAGES = ("ingest", "preprocess", "train", "package")
SELECTION_DOMAIN = "ConveyorFlow-ecological-v1-20261006"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ml_pool(source, calibration_per_corpus=12, main_per_corpus=6):
    old = {(v["corpus"], tuple(sorted(v["excluded_features"]))) for v in source["variants"]}
    output = []
    for corpus in ("adult", "beijing"):
        features = sorted(f for f in source["corpora"][corpus]["features"] if f != "timestamp")
        combos = [c for width in (2, 3) for c in itertools.combinations(features, width)
                  if (corpus, c) not in old]
        combos.sort(key=lambda c: hashlib.sha256((SELECTION_DOMAIN + ":" + corpus + ":" + ",".join(c)).encode()).hexdigest())
        needed = calibration_per_corpus + main_per_corpus
        if len(combos) < needed:
            raise ValueError("Insufficient disjoint ML specification population")
        for index, excluded in enumerate(combos[:needed]):
            split = "calibration" if index < calibration_per_corpus else "main"
            position = index + 1 if split == "calibration" else index - calibration_per_corpus + 1
            case_id = ("CAL" if split == "calibration" else "MAIN") + "_" + corpus.upper() + "_" + str(position).zfill(2)
            output.append({"case_id": case_id, "split": split, "corpus": corpus,
                           "cluster_id": corpus, "excluded_features": list(excluded),
                           "stages": list(STAGES), "minimum_train_rows": 20000,
                           "source_rows_reused": True, "not_data_split_holdout": True,
                           "reference_preflight_status": "not_executed",
                           "difficulty_labels_status": "not_human_expert_labeled"})
    return output


def repository_pool(source, excluded, read_command, max_per_split_project=4):
    groups, counts = {}, {}
    for project in PROJECTS:
        candidates = []
        for item in source["candidates"]:
            if item["project"] != project or (project, str(item["bug_id"])) in excluded:
                continue
            if not item["python_version"].startswith("3.8."):
                continue
            command = shlex.split(read_command(item).strip())
            if len(command) != 2 or command[0] != "pytest" or not command[1].startswith(item["test_file"]):
                continue
            candidates.append(item)
        candidates.sort(key=lambda c: hashlib.sha256((SELECTION_DOMAIN + ":" + project + ":" + str(c["bug_id"])).encode()).hexdigest())
        counts[project] = len(candidates)
        needed = 2 * max_per_split_project
        if len(candidates) < needed:
            raise ValueError("Insufficient new supported repository pool: " + project)
        for split, begin in (("calibration", 0), ("main", max_per_split_project)):
            groups[(split, project)] = candidates[begin:begin + max_per_split_project]
    rows = []
    for split in ("calibration", "main"):
        for rank in range(max_per_split_project):
            for project in PROJECTS:
                item = groups[(split, project)][rank]
                rows.append({**item, "bug_id": str(item["bug_id"]), "split": split,
                             "pool_order_within_repository": rank,
                             "case_id": project + "_" + str(item["bug_id"]),
                             "reference_preflight_status": "not_executed",
                             "not_guaranteed_unseen_in_pretraining": True})
    return rows, counts


def prior_repository_population():
    # Exclude entire earlier predeclared pools, not only successful model cases.
    paths = [MAJOR / "results/bugsinpy_calibration_preflight_v1/manifest.json",
             MAJOR / "results/bugsinpy_serial_build_recovery_v6_protocol/combined_prefix_ledger.jsonl",
             MAJOR / "repository_repair_pilot_v1_lock.json", MAJOR / "repository_first_attempt_v1_lock.json"]
    excluded = set()
    inventory = []
    for path in paths:
        if path.suffix == ".jsonl":
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        else:
            content = json.loads(path.read_text(encoding="utf-8"))
            rows = content.get("cases", content.get("candidates", []))
        for row in rows:
            excluded.add((row["project"], str(row["bug_id"])))
        inventory.append({"path": path.relative_to(V2).as_posix(), "sha256": sha256(path)})
    return excluded, inventory


def prepare():
    if DEST.exists():
        raise FileExistsError("Preparation capsule exists; audit it, never overwrite")
    ml_source = MAJOR / "ml_cases/case_manifest.json"
    bugs_source = MAJOR / "bugsinpy_candidate_manifest.json"
    ml = ml_pool(json.loads(ml_source.read_text(encoding="utf-8")))
    excluded, exposure = prior_repository_population()
    bugs, supported = repository_pool(json.loads(bugs_source.read_text(encoding="utf-8")), excluded,
        lambda item: (V2 / "bip/projects" / item["project"] / "bugs" / str(item["bug_id"]) / "run_test.sh").read_text(encoding="utf-8"))
    provider = V2 / "real_llm_pilot/config.mfec_main_frozen.json"
    models = [{k: m[k] for k in ("slot", "model_id", "exact_version")}
              for m in json.loads(provider.read_text(encoding="utf-8"))["models"]]
    dependencies = {"prepare_design.py": sha256(Path(__file__)), "ml_source_manifest": sha256(ml_source),
                    "bugs_source_manifest": sha256(bugs_source), "provider_config": sha256(provider),
                    "protocol": sha256(HERE / "PROTOCOL_TH.md")}
    design = {"status": "prepared_outcome_blind_pools_not_execution_ready",
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "models": models,
              "selection_domain": SELECTION_DOMAIN, "dependencies": dependencies,
              "excluded_repository_cases": [list(x) for x in sorted(excluded)],
              "prior_population_evidence": exposure, "supported_repository_counts": supported,
              "ml_specifications": ml, "repository_preflight_pool": bugs,
              "repository_target_per_split_per_repository": 2,
              "repository_max_preflights_per_split_per_repository": 4,
              "calibration_if_full_pool_preflights_pass": {"ml_specs": 24, "ml_stage_probes": 96,
                  "bug_cases": 6, "planned_generation_calls": 306,
                  "max_output_tokens_per_call": 32768, "max_output_tokens_total": 10027008,
                  "status": "design_envelope_not_approved_spend"},
              "budget_status": "awaiting_user_limit_and_precision_freeze",
              "main_sample_size_status": "not_frozen",
              "paid_execution_allowed": False, "no_provider_calls": True,
              "not_human_expert_labels": True, "source_corpora": 2,
              "no_independence_claim_for_variants": True,
              "execution_blockers": ["budget_and_precision_not_frozen", "new_reference_gates_not_executed",
                  "new_repository_environments_not_preflighted", "no_ecological_ability_profiles",
                  "live_assessor_executor_verifier_integration_not_audited",
                  "actual_decision_process_and_claim_paths_not_validated", "approval_quota_unresolved"]}
    DEST.mkdir()
    manifest = DEST / "design.json"
    manifest.write_text(json.dumps(design, indent=2) + "\n", encoding="utf-8")
    lock = {"status": "preparation_identity_lock_not_paid_execution_authorization",
            "design_sha256": sha256(manifest), "dependencies": dependencies,
            "no_provider_calls": True, "paid_execution_allowed": False}
    (DEST / "lock.json").write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    return {"status": design["status"], "ml_calibration_specs": 24, "ml_main_specs": 12,
            "repository_preflight_pool": len(bugs), "design_sha256": lock["design_sha256"],
            "paid_execution_allowed": False, "no_provider_calls": True}


def audit():
    design = json.loads((DEST / "design.json").read_text(encoding="utf-8"))
    lock = json.loads((DEST / "lock.json").read_text(encoding="utf-8"))
    if sha256(DEST / "design.json") != lock["design_sha256"] or design["paid_execution_allowed"]:
        raise ValueError("Preparation identity or execution guard changed")
    paths = {"prepare_design.py": Path(__file__), "ml_source_manifest": MAJOR / "ml_cases/case_manifest.json",
             "bugs_source_manifest": MAJOR / "bugsinpy_candidate_manifest.json",
             "provider_config": V2 / "real_llm_pilot/config.mfec_main_frozen.json", "protocol": HERE / "PROTOCOL_TH.md"}
    if {name: sha256(path) for name, path in paths.items()} != lock["dependencies"]:
        raise ValueError("Preparation dependency changed")
    ml_signatures = [(x["corpus"], tuple(x["excluded_features"])) for x in design["ml_specifications"]]
    bug_signatures = [(x["project"], x["bug_id"]) for x in design["repository_preflight_pool"]]
    if len(ml_signatures) != len(set(ml_signatures)) or len(bug_signatures) != len(set(bug_signatures)):
        raise ValueError("Duplicate or overlapping specification")
    excluded, current = prior_repository_population()
    if current != design["prior_population_evidence"] or any(x in excluded for x in bug_signatures):
        raise ValueError("Repository population overlap or prior evidence changed")
    return {"status": "preparation_identity_verified_not_live_ready", "no_provider_calls": True,
            "paid_execution_allowed": False, "design_sha256": lock["design_sha256"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    print(json.dumps(audit() if args.audit else prepare()))
