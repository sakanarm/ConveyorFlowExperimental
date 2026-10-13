"""Freeze a new 12-block mixed ML/repository exact-edits allocation study.

All case, verifier, prompt, profile and executable identities are checked
before a paid route can be enabled. This module itself cannot call an LLM.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import build_repair_candidates_v1b as candidates
import audit_candidates_v1b as candidate_auditor
import audit_regression_preselection_v1c as regression_auditor
import prepare_repair_contexts_v1c as contexts
import audit_repair_contexts_v1c as context_auditor
import select_repair_cases_v1 as selection

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
MAJOR = V2 / "major_revision_v2_3"
ECO = MAJOR / "ecological_v1"
sys.path.insert(0, str(MAJOR))
sys.path.insert(0, str(ECO))
from audit_preparation import audit_ml  # noqa: E402
from audit_main_capability_profiles_v1 import audit as audit_profiles  # noqa: E402
from belt_contract import Agent, Limits, Task, validate_tasks  # noqa: E402
from freeze_ecological_main_v1 import static_owners  # noqa: E402
from main_artifact_chain_v1 import PREDECESSOR  # noqa: E402
from main_live_ml_bundle_v1 import PUBLIC_FILES  # noqa: E402
from prepare_design import DEST, audit as audit_design  # noqa: E402
from run_repository_first_attempt_v1 import INSTRUCTION  # noqa: E402

ROOT = HERE / "results/main_v1"
LOCK = ROOT / "execution_lock.json"
PROFILE = ECO / "main_capability_profiles_v1.json"
PROVIDER = V2 / "real_llm_pilot/config.mfec_main_frozen.json"
ARMS = ("CF_FIT", "CENTRAL_RULE_MATCHED", "STATIC_OWNERS")
ORDERS = ((0, 1, 2), (1, 2, 0), (2, 0, 1),
          (0, 2, 1), (1, 0, 2), (2, 1, 0))
STAGES = ("ingest", "preprocess", "train", "package")
RANKS = {"ingest": 1, "preprocess": 2, "train": 3, "package": 2}
RUNTIME = "/mnt/d/ConveyorFlowRuntime/v2_4/main_exact_edits_v1"
ML_RUNTIME = "/mnt/d/ConveyorFlowRuntime/v2_4/ml_main_exact_edits_v1"
REPAIR_RUNTIME = "/mnt/d/ConveyorFlowRuntime/v2_4/repair_main_exact_edits_v1"
NEW_SOURCES = ("freeze_main_v1.py", "run_main_v1.py", "ml_adapter_v1.py",
               "repair_adapter_v1.py", "audit_main_v1.py", "analyze_main_v1.py",
               "wsl_main_bridge_v1.py", "build_repair_candidates_v1b.py",
               "preselect_regressions_v1b.py", "preselect_regressions_v1c.py",
               "source_scope_v1c.json", "regression_manifest_v1c.json")
NEW_SOURCES += ("audit_candidates_v1b.py",
                "audit_regression_preselection_v1c.py",
                "prepare_repair_contexts_v1b.py",
                "run_context_queue_v1b.py",
                "audit_repair_contexts_v1b.py",
                "prepare_repair_contexts_v1c.py",
                "run_context_queue_v1c.py",
                "audit_repair_contexts_v1c.py")
OLD_SOURCES = ("belt_contract.py", "claim_store.py", "integration_worker_v1.py",
               "integration_backend_v1.py", "live_allocator_core_v1.py",
               "analyze_ecological_main_v1.py",
               "main_artifact_chain_v1.py", "main_live_ml_bundle_v1.py",
               "main_live_ml_stage_v1.py", "main_stage_compatibility_v1.py",
               "freeze_ecological_main_v1.py", "prepare_repository_main_contexts_v1.py",
               "run_repository_calibration.py", "run_ml_calibration.py")
MAJOR_SOURCES = ("run_repository_first_attempt_v1.py",
                 "repository_exact_edits_v3.py", "repository_patch_guard_v1.py",
                 "run_repository_repair_pilot_v1.py", "run_ml_dag_llm_feasibility.py",
                 "run_ml_container.py", "container_cli.py")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Required nonsymlink file absent: " + str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def ml_cases() -> tuple[list[str], dict[str, str]]:
    design = audit_design()
    specs = {row["case_id"]: row for row in read(DEST / "design.json")["ml_specifications"]
             if row["split"] == "main"}
    ordered = [f"MAIN_{name}_{index:02d}"
               for index in range(1, 7) for name in ("ADULT", "BEIJING")]
    if set(ordered) != set(specs):
        raise ValueError("Frozen public Adult/Beijing ML cohort changed")
    hashes = {}
    for cid in ordered:
        prepared = ECO / "ml_preparation" / cid
        audit_ml(prepared, specs[cid], design["design_sha256"])
        public = prepared / "public"
        if {p.relative_to(public).as_posix() for p in public.rglob("*") if p.is_file()} != set(PUBLIC_FILES):
            raise ValueError("Prepared public ML file set changed: " + cid)
        hashes[cid] = sha256(prepared / "summary.json")
    return ordered, hashes


def repository_cases() -> tuple[list[dict], dict[str, str]]:
    prepared = contexts.freeze()
    if len(prepared["cases"]) != 12:
        raise ValueError("Twelve gold-free repository cases required")
    by_project = {project: [] for project in selection.PROJECTS}
    hashes = {}
    for case in prepared["cases"]:
        cid = case["case_id"]
        row = read(contexts.ROOT / cid / "summary.json")
        baseline = read(candidates.ROOT / cid / "summary.json")
        if (row["status"] != "context_identity_passed" or
                row["source_mutation_import_confirmed"] is not True or
                baseline["status"] != "candidate_preflight_passed" or
                row["candidate_summary_sha256"] != sha256(
                    candidates.ROOT / cid / "summary.json") or
                row["full_context_sha256"] != sha256(
                    contexts.ROOT / cid / "full_buggy_context.json") or
                row["prompt_context_sha256"] != sha256(
                    contexts.ROOT / cid / "prompt_context.json")):
            raise ValueError("Repository context/validator gate mismatch: " + cid)
        prompt_context = read(contexts.ROOT / cid / "prompt_context.json")
        if ("allowed_source_files" in prompt_context or
                prompt_context["allowed_paths"] != case["allowed_files"]):
            raise ValueError("Fixed/full-source leakage or allowed-path drift")
        prompt = INSTRUCTION + json.dumps(prompt_context, ensure_ascii=False)
        enriched = {**case,
                    "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    "preparation_root": "../major_revision_v2_4/results/repair_contexts_v1c",
                    "baseline_root": "../major_revision_v2_4/results/candidates_v1b",
                    "preparation_summary_sha256": sha256(contexts.ROOT / cid / "summary.json")}
        by_project[case["project"]].append(enriched)
        hashes[cid] = enriched["preparation_summary_sha256"]
    if any(len(rows) != 3 for rows in by_project.values()):
        raise ValueError("Three qualified cases per source repository required")
    # Interleave repositories so that wall-clock order and one project are not confounded.
    ordered = [by_project[project][index]
               for index in range(3) for project in selection.PROJECTS]
    return ordered, hashes


def plan() -> tuple[dict, dict[str, str]]:
    if (context_auditor.audit()["status"] !=
            "all_amended_contexts_independently_audited" or
            read(context_auditor.OUTPUT) != context_auditor.audit()):
        raise ValueError("Amended contexts not independently audited/sealed")
    if read(regression_auditor.OUTPUT) != regression_auditor.audit():
        raise ValueError("Sealed independent public regression selection audit drift")
    candidate_audit = candidate_auditor.audit()
    if (candidate_audit["status"] != "all_candidate_gates_independently_audited" or
            read(candidate_auditor.OUTPUT) != candidate_audit):
        raise ValueError("Independent amended candidate gate audit incomplete/unsealed")
    if audit_profiles().get("profiles") != 3:
        raise ValueError("Historical operational ability profiles not audited")
    provider = read(PROVIDER)
    roster = provider["models"]
    profile = read(PROFILE)
    if len(roster) != 3 or set(profile["profiles"]) != {row["slot"] for row in roster}:
        raise ValueError("Three-model ability roster differs from audited v2.3 profile")
    agents = tuple(Agent("A" + str(index + 1), model["slot"],
                         profile["profiles"][model["slot"]]["routing_ranks"])
                   for index, model in enumerate(roster))
    ml_order, ml_hashes = ml_cases()
    repair_order, repair_hashes = repository_cases()
    if len(ml_order) != 12 or len(repair_order) != 12:
        raise AssertionError("Expected twelve unique mixed blocks")
    limits = Limits(scan=8, w1=2, w2=4, no_volunteer_limit=6,
                    max_attempts=1, horizon=3600)
    blocks = []
    for index, (ml, repair) in enumerate(zip(ml_order, repair_order), 1):
        run_id = f"V24_BLOCK_{index:02d}"
        workload = "adult" if "ADULT" in ml else "beijing"
        tasks = [Task(f"{ml}:{stage}", ml, workload, stage, RANKS[stage], 0,
                      tuple(f"{ml}:{parent}" for parent in PREDECESSOR[stage]))
                 for stage in STAGES]
        tasks.insert(1, Task(f"{repair['case_id']}:repair", repair["case_id"],
                             "bugs2fix", "repair", 2, 20))
        validate_tasks(tasks)
        permutation = ORDERS[(index - 1) % len(ORDERS)]
        blocks.append({"block_id": run_id, "run_id": run_id,
                       "case_ids": [ml, repair["case_id"]],
                       "arm_order": [ARMS[position] for position in permutation],
                       "tasks": [{**asdict(task),
                                  "dependencies": list(task.dependencies)} for task in tasks],
                       "owners": static_owners(tasks, agents), "seed": 7100 + index})
    prompts = {case["case_id"]: INSTRUCTION + json.dumps(
        read(contexts.ROOT / case["case_id"] / "prompt_context.json"),
        ensure_ascii=False) for case in repair_order}
    if any(hashlib.sha256(prompts[case["case_id"]].encode("utf-8")).hexdigest() !=
           case["prompt_sha256"] for case in repair_order):
        raise ValueError("Frozen exact-edits prompt construction mismatch")
    stable = {
        "status": "v2_4_exact_edits_mixed_main_frozen",
        "paid_execution_allowed": True, "research_results_before_audit": False,
        "post_v2_3_protocol_not_preregistered_for_v2_3": True,
        "matched_decision_rule": "Agent-local versus coordinator process; same fit/stand-down, task belt, CAS, executor and verifier",
        "arm_ids": list(ARMS), "run_ids": [row["run_id"] for row in blocks],
        "models": {row["slot"]: {key: row[key] for key in ("model_id", "exact_version")}
                   for row in roster},
        "agents": [{**asdict(agent), "declined_tasks": []} for agent in agents],
        "ml_case_ids": ml_order,
        "repository_case_ids": [row["case_id"] for row in repair_order],
        "repository_cases": repair_order,
        "blocks": blocks, "limits": asdict(limits),
        "tick_ns": 1_000_000_000, "max_wall_seconds_per_arm": 5400,
        "max_provider_calls_per_arm": 5, "max_provider_calls_overall": 180,
        "generation": {"temperature": 0, "max_output_tokens": 32768,
                       "timeout_seconds": 720},
        "repository_test_timeout_seconds": 180,
        "runtime_root": RUNTIME, "ml_runtime_root": ML_RUNTIME,
        "repair_runtime_root": REPAIR_RUNTIME,
        "design_sha256": audit_design()["design_sha256"],
        "profile_sha256": sha256(PROFILE),
        "provider_config_sha256": sha256(PROVIDER),
        "context_lock_sha256": sha256(contexts.LOCK),
        "context_audit_sha256": sha256(context_auditor.OUTPUT),
        "candidate_lock_sha256": sha256(candidates.LOCK),
        "candidate_amendment_lock_sha256": sha256(candidates.AMENDMENT_LOCK),
        "candidate_audit_sha256": sha256(candidate_auditor.OUTPUT),
        "regression_preselection_audit_sha256": sha256(
            regression_auditor.OUTPUT),
        "ml_preparation_summary_sha256": ml_hashes,
        "repository_context_summary_sha256": repair_hashes,
        "analysis_plan": {
            "primary_metrics": ["verified_job_throughput_fixed_window",
                                "successful_job_completion_time",
                                "busy_and_productive_utilization",
                                "provider_reported_cost_per_verified_job"],
            "secondary_metrics": ["verified_repository_repair_rate",
                                  "verified_ml_pipeline_rate", "dead_letter",
                                  "unresolved", "tokens"],
            "paired_unit": "mixed block", "source_repository_cluster": True,
            "comparisons": ["CF_FIT-CENTRAL_RULE_MATCHED",
                            "CF_FIT-STATIC_OWNERS"],
            "no_stage_pseudoreplication": True,
            "no_composite_or_universal_superiority": True,
            "no_population_equivalence_claim": True,
            "cost_undefined_if_attempt_cost_unknown": True,
        },
        "dependencies_sha256": {
            **{name: sha256(HERE / name) for name in NEW_SOURCES},
            **{name: sha256(ECO / name) for name in OLD_SOURCES},
            **{name: sha256(MAJOR / name) for name in MAJOR_SOURCES},
            "protocol": sha256(HERE / "PROTOCOL_TH.md"),
            "candidate_instrument_amendment": sha256(
                HERE / "CANDIDATE_AMENDMENT_V1B_TH.md"),
            "candidate_path_amendment": sha256(
                HERE / "CANDIDATE_AMENDMENT_V1C_TH.md"),
            "context_amendment": sha256(
                HERE / "CONTEXT_AMENDMENT_V1B_TH.md"),
            "context_amendment_v1c": sha256(
                HERE / "CONTEXT_AMENDMENT_V1C_TH.md"),
            "profile_auditor": sha256(ECO / "audit_main_capability_profiles_v1.py"),
            "provider_adapter": sha256(V2 / "real_llm_pilot/mfec_adapter.py"),
            "ml_evaluator_lock": sha256(MAJOR / "ml_eval_image_lock_podman_v1.json"),
        },
    }
    return stable, prompts


def freeze() -> dict:
    stable, prompts = plan()
    if LOCK.exists():
        previous = read(LOCK)
        if any(previous.get(key) != value for key, value in stable.items()):
            raise ValueError("Frozen paid instrument/case/profile drift")
        for cid, prompt in prompts.items():
            if sha256(ROOT / "frozen_prompts" / (cid + ".txt")) != hashlib.sha256(
                    prompt.encode("utf-8")).hexdigest():
                raise ValueError("Frozen gold-free prompt drift")
        return previous
    if ROOT.exists():
        raise FileExistsError("Paid main root exists without lock")
    ROOT.mkdir(parents=True)
    (ROOT / "frozen_prompts").mkdir()
    for cid, prompt in prompts.items():
        with (ROOT / "frozen_prompts" / (cid + ".txt")).open(
                "x", encoding="utf-8", newline="\n") as stream:
            stream.write(prompt)
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


if __name__ == "__main__":
    if sys.argv[1:] != ["--freeze"]:
        raise SystemExit("Only --freeze; this module has no paid route")
    result = freeze()
    print(json.dumps({"status": result["status"], "blocks": len(result["blocks"]),
                      "lock_sha256": sha256(LOCK), "provider_calls": 0}))
