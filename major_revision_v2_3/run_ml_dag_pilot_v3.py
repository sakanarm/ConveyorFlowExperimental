"""Bounded exploratory DAG feasibility with preserved per-stage attempts.

No generated code runs on the host. Every attempt has a fresh public-only
bundle and the same locked OCI image. Prior negative results remain unchanged.
"""
import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from materialize_ml_bundle import materialize
from run_ml_container import WORKSPACES, LOCK
from run_ml_dag_llm_feasibility import (PILOT, STAGES, SCRIPT, build_prompt,
    decode_stage_source, generation_failure_report, preflight_container, invoke)
from run_ml_dag_stage import run_stage, sha256

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config_ml_dag_pilot_v3.json"
FROZEN = HERE / "ml_dag_pilot_v3_lock.json"

INTERFACE = (
    "\nShared artifact and dtype contract for all models: CSV missing values "
    "are empty strings or NaN. Use ordinary numpy float64 with np.nan for numeric "
    "missing values and ordinary object/string arrays for categorical values; "
    "do not pass pandas pd.NA or nullable extension arrays into sklearn. Do not "
    "include row_id, target, or timestamp in features. Use the same conversion "
    "during training and fresh-process inference. Save only dictionaries, lists, "
    "numpy values, and importable library estimators in joblib artifacts, not "
    "custom __main__ classes, lambdas, closures, or dynamically defined "
    "transformers. Include feature order and any fitted category mappings in "
    "the artifacts. Scripts execute separately, so model.joblib must include "
    "all preprocessing state needed for prediction. Return concise complete "
    "source for the current stage only, without an explanation or discussion. "
    "The runtime allows 2 CPUs, 4 GiB memory and a 360-second stage timeout."
)


def input_hashes() -> dict:
    paths = {"config": CONFIG, "runner": Path(__file__),
             "prompt_builder": HERE / "run_ml_dag_llm_feasibility.py",
             "stage_runner": HERE / "run_ml_dag_stage.py",
             "validator": HERE / "validate_ml_outputs.py",
             "quality_gates": HERE / "ml_cases" / "quality_gates.json",
             "case_manifest": HERE / "ml_cases" / "case_manifest.json",
             "provider_config": PILOT / "config.mfec_main_frozen.json",
             "provider_adapter": PILOT / "mfec_adapter.py",
             "credential_bridge": HERE / "wsl_provider_bridge.py",
             "evaluator_lock": LOCK}
    return {name: sha256(path) for name, path in paths.items()}


def freeze() -> dict:
    settings = json.loads(CONFIG.read_text(encoding="utf-8"))
    current = input_hashes()
    if FROZEN.exists():
        frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
        if frozen["input_sha256"] != current:
            raise ValueError("frozen v3 protocol dependencies changed")
        return frozen
    ready = preflight_container()
    frozen = {"status": "frozen_before_v3_provider_calls",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "input_sha256": current, "settings": settings,
              "container_preflight": ready,
              "interface_sha256": hashlib.sha256(INTERFACE.encode()).hexdigest()}
    FROZEN.write_text(json.dumps(frozen, indent=2) + "\n", encoding="utf-8")
    return frozen


def run_job(case_id: str, slot: str) -> dict:
    frozen = freeze()
    settings = frozen["settings"]
    if case_id not in settings["case_ids"] or slot not in settings["model_slots"]:
        raise ValueError("case/model is outside the frozen six-job feasibility plan")
    root = WORKSPACES / f"{case_id}_{slot}_pilot_v3"
    if root.exists():
        raise FileExistsError("prior v3 job exists; inspect it, do not rerun or overwrite")
    provider_config = json.loads((PILOT / "config.mfec_main_frozen.json").read_text(encoding="utf-8"))
    model = next(item for item in provider_config["models"] if item["slot"] == slot)
    preflight_container()  # before any provider call
    root.mkdir()
    started = {"status": "exploratory_v3_started", "case_id": case_id,
               "model_slot": slot, "model_id": model["model_id"],
               "lock_sha256": sha256(FROZEN), "research_results": False,
               "started_at_utc": datetime.now(timezone.utc).isoformat()}
    (root / "job_started.json").write_text(json.dumps(started, indent=2) + "\n", encoding="utf-8")
    verified_bundles = {}
    attempts = []
    outcome = "VERIFIED"
    for stage in STAGES:
        passed = False
        feedback = None
        previous_source = None
        for attempt in range(1, settings["max_attempts_per_stage"] + 1):
            bundle = root / f"{stage}_attempt_{attempt}"
            materialize(case_id, bundle)
            for predecessor, prior in verified_bundles.items():
                shutil.copy2(prior / "submission" / SCRIPT[predecessor],
                             bundle / "submission" / SCRIPT[predecessor])
                shutil.copytree(prior / "dag_output" / predecessor,
                                bundle / "dag_output" / predecessor)
            prompt = build_prompt(bundle, stage) + INTERFACE
            if feedback:
                prompt += ("\nPrevious attempt for this same stage failed. Produce a new complete "
                           "script, using only this current-stage feedback.\n" +
                           json.dumps({"previous_source": previous_source,
                                       "current_stage_error": feedback}, ensure_ascii=False))
            prompt_path = bundle / "prompt.txt"
            prompt_path.write_text(prompt, encoding="utf-8")
            request = {"stage": stage, "attempt": attempt,
                       "prompt_sha256": sha256(prompt_path),
                       "lock_sha256": sha256(FROZEN),
                       "started_at_utc": datetime.now(timezone.utc).isoformat()}
            (bundle / "request_started.json").write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"case": case_id, "slot": slot, "stage": stage,
                              "attempt": attempt, "status": "provider_request_started"}), flush=True)
            try:
                response = invoke(model={**model, "base_url": provider_config["base_url"]},
                                  case={"prompt": prompt}, generation=settings["generation"])
            except Exception as error:
                # Do not retry a request with an unknown billable outcome.
                report = {"status": "provider_unresolved", "error_type": type(error).__name__,
                          "billable_outcome_unknown": True, "automatic_retry": False}
                (bundle / "provider_error.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                attempts.append({**request, **report, "bundle": str(bundle.relative_to(HERE))})
                outcome = "PROVIDER_UNRESOLVED"
                break
            content = str(response.pop("content"))
            (bundle / "response.txt").write_text(content, encoding="utf-8")
            metadata = {"provider": response, "prompt_sha256": sha256(prompt_path),
                        "response_sha256": sha256(bundle / "response.txt")}
            (bundle / "provider.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
            if response["exact_model_version"] != model["exact_version"]:
                attempts.append({**request, "status": "deployment_mapping_drift",
                                 "bundle": str(bundle.relative_to(HERE))})
                outcome = "PROVIDER_UNRESOLVED"
                break
            try:
                source = decode_stage_source(stage, content, response["finish_reason"])
            except (ValueError, SyntaxError) as error:
                result = generation_failure_report(bundle, case_id, stage,
                                                   f"{type(error).__name__}: {error}")
                previous_source = content[:20000]
            else:
                (bundle / "submission" / SCRIPT[stage]).write_text(source, encoding="utf-8")
                result = run_stage(case_id, bundle, stage)
                previous_source = source
            record = {**request, "bundle": str(bundle.relative_to(HERE)),
                      "provider_metadata_sha256": sha256(bundle / "provider.json"),
                      "stage_report_sha256": sha256(bundle / "dag_output" / stage / "stage_report.json"),
                      "verified": result["verified"], "failure_class": result.get("failure_class")}
            attempts.append(record)
            print(json.dumps({"case": case_id, "slot": slot, "stage": stage,
                              "attempt": attempt, "verified": result["verified"],
                              "failure_class": result.get("failure_class")}), flush=True)
            if result.get("failure_class") in {"container_start_failure", "execution_timeout_unresolved"}:
                outcome = "ENVIRONMENT_UNRESOLVED"
                break
            if result["verified"]:
                passed = True
                verified_bundles[stage] = bundle
                break
            # Final hidden scores never enter model feedback.
            feedback = {"failure_class": result.get("failure_class"),
                        "failure_reason": result.get("failure_reason"),
                        "stderr_tail": result.get("execution", {}).get("stderr_tail", "")}
        if not passed:
            if outcome == "VERIFIED":
                outcome = "DEAD_LETTER"
            break
    summary = {**started, "status": "exploratory_v3_completed",
               "completed_at_utc": datetime.now(timezone.utc).isoformat(),
               "job_outcome": outcome, "verified_stages": list(verified_bundles),
               "attempts": attempts, "provider_attempts": len(attempts),
               "not_a_policy_comparison": True, "not_probability_calibration": True,
               "case_reuse": settings["case_reuse"], "ability_rank_is_placeholder": True}
    (root / "pilot_v3_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--case-id")
    parser.add_argument("--model-slot")
    args = parser.parse_args()
    if args.freeze:
        print(json.dumps(freeze(), indent=2))
    elif args.case_id and args.model_slot:
        print(json.dumps(run_job(args.case_id, args.model_slot), indent=2))
    else:
        parser.error("use --freeze or provide --case-id and --model-slot")
