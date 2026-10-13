"""Bounded, independently reached ML stages; not a policy experiment.

One provider invocation per pair; no automatic paid retry. Current candidate
source and joblib are executed/read ONLY in the pinned Podman sandbox.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from prepare_ml_isolated_stage_pilot_v1 import ROOT as PREP, CASES, write
from run_ml_dag_stage import ARTIFACT, PREDECESSOR, SCRIPT, STAGES, sha256
from run_ml_dag_llm_feasibility import build_prompt, decode_stage_source, preflight_container, invoke
from ml_stage_probe_sandbox_v1 import run_named_stage, verify_artifact

HERE = Path(__file__).resolve().parent
ROOT = HERE / "candidate_workspaces/ml_isolated_stage_pilot_v1"
LOCK = HERE / "ml_isolated_stage_pilot_v1_lock.json"
PROVIDER = HERE.parent / "real_llm_pilot/config.mfec_main_frozen.json"
SLOTS = ("agent_1", "agent_2", "agent_3")
GENERATION = {"temperature": 0, "max_output_tokens": 32768, "timeout_seconds": 720}
INTERFACE = """
This NEW isolated-stage experiment uses trusted predecessor state. Other
stages' model outcomes never determine whether this stage is reached. Follow
this deliberately narrow public ordinal-state interface exactly:
columns = training CSV columns in original order, excluding row_id, target,
timestamp. For each NONNUMERIC training column (as inferred by pandas.read_csv),
map sorted unique training values after fillna('__MISSING__').astype(str) to
integers 0,1,... . Do not add validation/test-only categories. Preprocessor
joblib must be exactly {'columns': columns, 'mappings': mappings}. Transform
categoricals with that mapping and unknown=-1, cast float; numeric columns use
pd.to_numeric(errors='coerce').astype(float), preserving np.nan. Do not add
scalers or imputers to the preprocessor artifact. The train-stage estimator
may handle or impute NaNs internally using an importable sklearn Pipeline.
Model joblib must be exactly {'columns': columns, 'mappings': mappings,
'model': fitted importable sklearn estimator, 'classification': bool}.
Classification is True for Adult and False for Beijing. Model estimator must
consume the public transformed feature frame. For classification return
positive-class probabilities; regression returns finite PM2.5 predictions.
No custom __main__ classes/lambdas/closures in joblib. Train fit uses training
rows only. Never fit on test or reveal hidden labels. This is an interface
test, not an unrestricted AutoML benchmark. No future reference solution or
hidden reference score is supplied. Return concise complete current-stage
source in the required single-key JSON, no commentary. Runtime: 2 CPUs/4 GiB,
360 seconds per execution, OMP/OpenBLAS/MKL/NumExpr threads=2, no network.
"""


def now():
    return datetime.now(timezone.utc).isoformat()


def dependencies():
    names = ("run_ml_isolated_stage_pilot_v1.py", "wsl_ml_stage_probe_bridge_v1.py",
             "prepare_ml_isolated_stage_pilot_v1.py", "ML_ISOLATED_STAGE_PILOT_V1_PROTOCOL_TH.md",
             "ml_stage_probe_sandbox_v1.py", "ml_stage_probe_verifier_v1.py",
             "run_ml_dag_llm_feasibility.py", "run_ml_dag_stage.py", "run_ml_container.py",
             "container_cli.py", "materialize_ml_bundle.py", "validate_ml_outputs.py", "reference_ml_gates.py")
    result = {n: sha256(HERE / n) for n in names}
    for n, p in {"provider_config": PROVIDER, "provider_adapter": PROVIDER.parent / "mfec_adapter.py",
                 "preparation": PREP / "summary.json", "evaluator": HERE / "ml_eval_image_lock_podman_v1.json",
                 "case_manifest": HERE / "ml_cases/case_manifest.json", "quality_gates": HERE / "ml_cases/quality_gates.json"}.items():
        result[n] = sha256(p)
    return result


def verify_preparation():
    prepared = json.loads((PREP / "summary.json").read_text())
    if prepared["status"] != "isolated_stage_reference_preparation_passed" or prepared["probe_count"] != 12:
        raise ValueError("all twelve reference probes must pass before provider calls")
    for row in prepared["rows"]:
        if not row["verified"] or not row["reference_only_not_llm_observation"]:
            raise ValueError("invalid reference observation")
        bundle = HERE / row["bundle"]
        for name, expected in row["file_sha256"].items():
            if sha256(bundle / name) != expected:
                raise ValueError("prepared reference evidence changed: " + name)
    return prepared


def freeze():
    if sys.platform != "linux" or os.environ.get("CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Linux Podman only")
    verify_preparation()
    current = dependencies()
    if LOCK.exists():
        frozen = json.loads(LOCK.read_text())
        if frozen["dependencies"] != current:
            raise ValueError("frozen isolated-stage dependency changed")
        return frozen
    if ROOT.exists():
        raise FileExistsError("unlocked output tree already exists")
    preflight = preflight_container()
    ROOT.mkdir()
    (ROOT / "frozen_prompts").mkdir()
    probes = []
    for case_id in CASES:
        for stage in STAGES:
            identity = case_id + "_" + stage
            prompt = build_prompt(PREP / identity, stage) + INTERFACE
            path = ROOT / "frozen_prompts" / (identity + ".txt")
            path.write_text(prompt, encoding="utf-8")
            probes.append({"probe_id": identity, "case_id": case_id, "stage": stage,
                           "corpus": "adult" if case_id.startswith("ADULT") else "beijing",
                           "prompt_sha256": sha256(path)})
    # Same hash order for all workers; don't select outcomes by difficulty.
    probes.sort(key=lambda p: hashlib.sha256(("ml-isolated-v1-20261005:" + p["probe_id"]).encode()).hexdigest())
    config = json.loads(PROVIDER.read_text())
    frozen = {"status": "frozen_before_isolated_stage_provider_calls", "created_at_utc": now(),
              "dependencies": current, "probes": probes, "model_slots": SLOTS,
              "models": [m for m in config["models"] if m["slot"] in SLOTS],
              "generation": GENERATION, "max_provider_calls": 36, "max_attempts_per_pair": 1,
              "container_preflight": preflight, "not_probability_fit": True,
              "not_allocation_comparison": True, "source_corpora": 2}
    write(LOCK, frozen)
    return frozen


@contextmanager
def execution_slot():
    import fcntl
    started = time.monotonic()
    with (ROOT / "container_serialization.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield time.monotonic() - started
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def public_bundle(probe, output):
    source = PREP / probe["probe_id"]
    output.mkdir()
    shutil.copy2(source / "bundle_manifest.json", output / "bundle_manifest.json")
    shutil.copytree(source / "input", output / "input")
    (output / "submission").mkdir()
    for previous in PREDECESSOR[probe["stage"]]:
        shutil.copy2(source / "submission" / SCRIPT[previous], output / "submission" / SCRIPT[previous])
        shutil.copytree(source / "dag_output" / previous, output / "dag_output" / previous)


def gates(probe, bundle, label):
    with execution_slot() as queue_seconds:
        result = run_named_stage(probe["case_id"], bundle, probe["stage"], label)
        compatibility = verify_artifact(probe["case_id"], bundle, probe["stage"], label) if result["verified"] and probe["stage"] in {"preprocess", "train"} else None
    execution = [result["execution"]] + ([compatibility["execution"]] if compatibility else [])
    unresolved = any(e.get("timed_out") or e.get("return_code") in {125, 126, 127} for e in execution)
    return {"verified": result["verified"] and (compatibility is None or compatibility["verified"]),
            "environment_unresolved": unresolved, "queue_seconds": queue_seconds,
            "stage_report": result, "compatibility": compatibility}


def run_pair(probe, model, frozen):
    root = ROOT / (probe["probe_id"] + "_" + model["slot"])
    if root.exists():
        raise FileExistsError("prior pair exists, never blindly retry a paid request")
    preflight_container()
    root.mkdir()
    public_bundle(probe, root / "attempt")
    path = ROOT / "frozen_prompts" / (probe["probe_id"] + ".txt")
    if sha256(path) != probe["prompt_sha256"]:
        raise ValueError("frozen prompt changed")
    shutil.copy2(path, root / "prompt.txt")
    request = {**probe, "slot": model["slot"], "model_alias": model["model_id"],
               "started_at_utc": now(), "provider_calls": 1, "lock_sha256": sha256(LOCK)}
    write(root / "request_started.json", request)
    print(json.dumps({**request, "status": "provider_request_started"}), flush=True)
    try:
        config = json.loads(PROVIDER.read_text())
        response = invoke(model={**model, "base_url": config["base_url"]},
                          case={"prompt": path.read_text()}, generation=frozen["generation"])
    except Exception as error:
        write(root / "provider_error.json", {"type": type(error).__name__, "billable_outcome_unknown": True, "automatic_retry": False})
        outcome = "PROVIDER_UNRESOLVED"
    else:
        content = str(response.pop("content"))
        (root / "response.txt").write_text(content, encoding="utf-8")
        write(root / "provider.json", response)
        request.update({"provider_sha256": sha256(root / "provider.json"), "response_sha256": sha256(root / "response.txt")})
        if response["exact_model_version"] != model["exact_version"]:
            outcome = "PROVIDER_MAPPING_UNRESOLVED"
        else:
            try:
                source = decode_stage_source(probe["stage"], content, response["finish_reason"])
            except (ValueError, SyntaxError) as error:
                write(root / "generation_error.json", {"type": type(error).__name__, "reason": str(error)})
                outcome = "GENERATION_CONTRACT_FAILED"
            else:
                script = root / "attempt/submission" / SCRIPT[probe["stage"]]
                script.write_text(source, encoding="utf-8")
                request["source_sha256"] = sha256(script)
                checked = gates(probe, root / "attempt", "first_attempt")
                write(root / "gates.json", checked)
                outcome = "ENVIRONMENT_UNRESOLVED" if checked["environment_unresolved"] else "STAGE_CONTRACT_FAILED"
                if checked["verified"]:
                    public_bundle(probe, root / "replay")
                    shutil.copy2(script, root / "replay/submission" / SCRIPT[probe["stage"]])
                    repeated = gates(probe, root / "replay", "fresh_replay")
                    write(root / "replay_gates.json", repeated)
                    outcome = "VERIFIED" if repeated["verified"] else ("REPLAY_UNRESOLVED" if repeated["environment_unresolved"] else "REPLAY_CONTRACT_FAILED")
    result = {**request, "status": outcome, "completed_at_utc": now(), "not_probability_fit": True,
              "not_allocation_comparison": True, "trusted_predecessors_not_candidate_pipeline": True}
    write(root / "summary.json", result)
    with (ROOT / ("ledger_" + model["slot"] + ".jsonl")).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result) + "\n")
    print(json.dumps(result), flush=True)
    return result


def run_slot(slot):
    frozen = freeze()
    if slot not in SLOTS or not os.environ.get("MFEC_LITELLM_API_KEY"):
        raise ValueError("known slot and process credential required")
    model = next(m for m in frozen["models"] if m["slot"] == slot)
    rows = []
    for probe in frozen["probes"]:
        job = ROOT / (probe["probe_id"] + "_" + slot)
        if job.exists():
            raise FileExistsError("slot has started evidence; inspect instead of relaunching")
    for probe in frozen["probes"]:
        rows.append(run_pair(probe, model, frozen))
    return {"slot": slot, "completed_pairs": len(rows)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--slot", choices=SLOTS)
    args = parser.parse_args()
    if args.freeze:
        r = freeze()
        print(json.dumps({"status": r["status"], "lock_sha256": sha256(LOCK), "probes": len(r["probes"]), "max_provider_calls": r["max_provider_calls"]}))
    elif args.slot:
        print(json.dumps(run_slot(args.slot)))
    else:
        parser.error("use --freeze or --slot")
