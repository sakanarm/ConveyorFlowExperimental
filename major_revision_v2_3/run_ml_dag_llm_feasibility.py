"""Single-model MFEC four-stage DAG feasibility; not a policy comparison.

Exactly one provider call is allowed per stage.  Candidate Python executes
only through the pinned, networkless Docker evaluator.  The frozen v2 main
allocation results and manuscript are not modified by this pilot.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dag_belt import DagBelt, StageSpec
from materialize_ml_bundle import materialize
from run_ml_container import LOCK, WORKSPACES
from run_ml_dag_stage import SCRIPT, STAGES, run_stage, sha256
from container_cli import executable, canonical_image_id


HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "real_llm_pilot"
sys.path.insert(0, str(PILOT))
from allocation_engine import AgentSpec, EngineConfig  # noqa: E402
from mfec_adapter import invoke  # noqa: E402


DIFFICULTY = {"ingest": 1, "preprocess": 2, "train": 3, "package": 2}
PROMPT_REVISION = "v2_missing_values_20261004"


def preflight_container() -> dict:
    """Fail before a billable model call unless the locked evaluator is usable."""
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    image = lock.get("image_id")
    if lock.get("status") != "locked" or not isinstance(image, str) or not image.startswith("sha256:"):
        raise ValueError("immutable ML evaluator image is not locked")
    if executable() == "podman" and lock.get("trusted_smoke_passed") is not True:
        raise ValueError("Podman evaluator reference smoke is not certified; no provider call was made")
    environment = {
        key: value for key, value in os.environ.items()
        if key != "MFEC_LITELLM_API_KEY"
    }
    try:
        info = subprocess.run(
            ["podman", "--version"] if executable() == "podman" else
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, text=True, timeout=20, check=False,
            env=environment,
        )
        version = info.stdout.strip().removeprefix("podman version ")
        if info.returncode != 0 or not re.fullmatch(r"\d+\.\d+(?:\.\d+)?[^\s]*", version):
            raise RuntimeError("Docker daemon is unavailable; no provider call was made")
        inspected = subprocess.run(
            [executable(), "image", "inspect", image, "--format", "{{.Id}}"],
            capture_output=True, text=True, timeout=20, check=False,
            env=environment,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("Docker preflight failed; no provider call was made") from error
    if inspected.returncode != 0 or canonical_image_id(inspected.stdout) != image:
        raise RuntimeError("locked evaluator image is unavailable; no provider call was made")
    return {"docker_server_version": version, "container_runtime": executable(), "image_id": image,
            "evaluator_lock_sha256": sha256(LOCK)}
CONTRACT = {
    "ingest": (
        "Read all three public CSVs, validate train/validation schema and at least "
        "20,000 train rows, and write JSON with exactly train_columns, "
        "validation_columns, test_columns, train_rows, validation_rows, test_rows. "
        "The columns fields are ordered lists of strings and row fields are integers. "
        "The CLI arguments are --train --validation --test --output."
    ),
    "preprocess": (
        "Write a Python script accepting --train --validation --ingest --output. "
        "Read the verified ingest JSON, fit all imputers/encoders/scalers ONLY on "
        "training rows, and save a nonempty preprocessor.joblib with enough "
        "information for the next stage to transform new rows. Never fit on "
        "validation or test rows. Handle pandas nullable dtypes and missing "
        "values so the fitted sklearn pipeline works with this pinned pandas/"
        "scikit-learn environment, and apply the same conversion at inference. "
        "The next stage can inspect your Python source."
    ),
    "train": (
        "Write a Python script accepting --train --validation --preprocessor "
        "--output-model. Load the prior preprocessor.joblib, transform train "
        "without leakage, train a classifier or regressor as appropriate, and "
        "write model.joblib containing everything needed for fresh-process "
        "inference. Validation may guide selection, but do not fit preprocessing "
        "on validation. Training/test labels are not in the same files."
    ),
    "package": (
        "Write a Python script accepting --model --test --output-predictions. "
        "Load the prior model.joblib in a fresh process; write predictions.csv "
        "with exactly row_id,prediction, one row per test_features.csv row. "
        "Adult requires positive-class probabilities [0,1]; Beijing requires "
        "finite numeric PM2.5 predictions. Test labels are unavailable."
    ),
}


def decode_stage_source(stage: str, content: str, finish_reason: str) -> str:
    if finish_reason != "stop":
        raise ValueError("truncated_or_incomplete_provider_output")
    if len(content) > 400000:
        raise ValueError("provider_output_exceeds_source_cap")
    files = json.loads(content)
    if not isinstance(files, dict) or set(files) != {SCRIPT[stage]}:
        raise ValueError("stage_source_schema_mismatch")
    source = files[SCRIPT[stage]]
    if not isinstance(source, str) or not source.strip() or "\x00" in source:
        raise ValueError("invalid_candidate_source")
    compile(source, SCRIPT[stage], "exec")  # Syntax check; no host execution.
    return source


def generation_failure_report(bundle: Path, case_id: str, stage: str,
                              reason: str, *, recovered: bool = False) -> dict:
    report = {
        "status": "generation_failed", "research_results": False,
        "case_id": case_id, "stage": stage, "verified": False,
        "artifact_sha256": None, "failure_class": reason,
        "container_execution_started": False,
        "recovered_from_preserved_provider_evidence": recovered,
    }
    path = bundle / "dag_output" / stage / "stage_report.json"
    if path.exists():
        raise FileExistsError("refusing to overwrite a stage report")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def public_samples(bundle: Path) -> list[dict]:
    samples = []
    for name in ("train", "validation", "test_features"):
        with (bundle / "input" / f"{name}.csv").open(
            "r", encoding="utf-8", newline=""
        ) as handle:
            reader = csv.DictReader(handle)
            rows = [next(reader, None), next(reader, None)]
            samples.append({
                "file": f"{name}.csv", "columns": reader.fieldnames,
                "example_rows": [row for row in rows if row is not None],
            })
    return samples


def build_prompt(bundle: Path, stage: str) -> str:
    if stage not in STAGES:
        raise ValueError("unknown stage")
    prior_code = {}
    for previous in STAGES[:STAGES.index(stage)]:
        path = bundle / "submission" / SCRIPT[previous]
        if not path.is_file():
            raise FileNotFoundError(f"previous stage source missing: {path}")
        prior_code[SCRIPT[previous]] = path.read_text(encoding="utf-8")
    identity = json.loads((bundle / "bundle_manifest.json").read_text(encoding="utf-8"))
    prompt = (
        f"Case {identity['case_id']}: build a complete executable "
        f"{identity['corpus']} ML pipeline using only the supplied public "
        "train.csv, validation.csv, and test_features.csv. "
        "Validation is for model selection; hidden test labels are unavailable. "
        f"Excluded features: {', '.join(identity['excluded_features']) or 'none'}. "
        + "\nThis is stage " + stage + " of a four-stage DAG on the READY belt. "
        + "Only the current stage is assigned to you. Prior verified source is "
        + "included so artifact formats can be handed off. Do not redo or edit "
        + "earlier stage scripts. Offline libraries: Python 3.12.8, numpy 1.26.4, "
        + "pandas 2.3.3, scikit-learn 1.7.1, joblib 1.5.1. No network or "
        + "package installs.\nCurrent stage contract: " + CONTRACT[stage]
        + "\nReturn exactly one JSON object with one string key, '"
        + SCRIPT[stage] + "', whose value is complete Python source. No markdown."
        + "\nPublic schemas and sample rows:\n"
        + json.dumps(public_samples(bundle), ensure_ascii=False)
        + "\nPrior verified Python source:\n"
        + json.dumps(prior_code, ensure_ascii=False)
    )
    if len(prompt) > 100000:
        raise ValueError("prompt too large for the frozen feasibility cap")
    return prompt


def pilot(case_id: str, model_slot: str, *, execute: bool) -> dict:
    config_path = PILOT / "config.mfec_main_frozen.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    model = next((item for item in config["models"] if item["slot"] == model_slot), None)
    if model is None:
        raise ValueError("unknown model slot")
    manifest = json.loads((HERE / "ml_cases" / "case_manifest.json").read_text(encoding="utf-8"))
    if case_id not in {item["case_id"] for item in manifest["variants"]}:
        raise ValueError("unknown prepared pilot case")
    bundle = WORKSPACES / f"{case_id}_{model_slot}_mfec_dag_feasibility"
    if not bundle.exists():
        materialize(case_id, bundle)
    if (bundle / "dag_summary.json").exists():
        raise FileExistsError("refusing to overwrite prior DAG feasibility result")
    first_prompt = build_prompt(bundle, "ingest")
    preflight = {
        "status": "ready_not_executed" if not execute else "execution_started",
        "research_results": False, "case_id": case_id,
        "model_slot": model_slot, "model_id": model["model_id"],
        "prompt_revision": PROMPT_REVISION,
        "config_sha256": sha256(config_path),
        "first_prompt_sha256": hashlib.sha256(first_prompt.encode()).hexdigest(),
        "api_key_present": bool(os.environ.get(model["api_key_env"])),
        "max_provider_calls": 4, "bundle": str(bundle),
        "runner_sha256": sha256(Path(__file__)),
    }
    if not execute:
        return preflight
    if not preflight["api_key_present"]:
        raise ValueError(f"set {model['api_key_env']} outside the repository before --execute")
    container = preflight_container()
    preflight["container_preflight"] = container
    belt = DagBelt(
        policy="CF_FIT",
        agents=[AgentSpec(model_slot, model["model_id"], {"ml_build": 3, "fix_bug": 3})],
        stages=[
            StageSpec(
                f"{case_id}:{stage}", case_id,
                "adult_ml" if case_id.startswith("ADULT") else "beijing_ml",
                DIFFICULTY[stage],
                () if index == 0 else (f"{case_id}:{STAGES[index - 1]}",),
            )
            for index, stage in enumerate(STAGES)
        ],
        seed=23, config=EngineConfig(max_attempts=1),
    )
    records = []
    environment_unresolved = False
    while not belt.terminal:
        assignments = belt.allocate_round()
        if len(assignments) != 1:
            raise AssertionError("linear feasibility DAG expected one stage claim")
        assignment = assignments[0]
        stage = assignment.task_id.split(":", 1)[1]
        prompt = build_prompt(bundle, stage)
        prompt_path = bundle / f"dag_prompt_{stage}.txt"
        response_path = bundle / f"dag_response_{stage}.txt"
        metadata_path = bundle / f"dag_provider_{stage}.json"
        if prompt_path.exists() or response_path.exists() or metadata_path.exists():
            raise FileExistsError("refusing to overwrite prior stage provider evidence")
        prompt_path.write_text(prompt, encoding="utf-8")
        (bundle / f"dag_request_started_{stage}.json").write_text(json.dumps({
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "case_id": case_id, "stage": stage, "model_slot": model_slot,
            "config_sha256": preflight["config_sha256"],
            "prompt_sha256": sha256(prompt_path),
            "runner_sha256": preflight["runner_sha256"],
            "credentials_recorded": False,
        }, indent=2) + "\n", encoding="utf-8")
        response = invoke(
            model={**model, "base_url": config["base_url"]},
            case={"prompt": prompt},
            generation={"temperature": 0, "max_output_tokens": 8192,
                        "timeout_seconds": 240},
        )
        content = str(response.pop("content"))
        response_path.write_text(content, encoding="utf-8")
        metadata_path.write_text(json.dumps({
            "stage": stage, "prompt_sha256": sha256(prompt_path),
            "response_sha256": sha256(response_path), "provider": response,
        }, indent=2) + "\n", encoding="utf-8")
        if response["exact_model_version"] != model["exact_version"]:
            raise ValueError("model version changed; stop before scoring")
        try:
            source = decode_stage_source(stage, content, response["finish_reason"])
        except (ValueError, SyntaxError) as error:
            stage_result = generation_failure_report(
                bundle, case_id, stage, f"{type(error).__name__}: {error}")
        else:
            script = bundle / "submission" / SCRIPT[stage]
            if script.exists():
                raise FileExistsError("refusing to overwrite candidate source")
            script.write_text(source, encoding="utf-8")
            stage_result = run_stage(case_id, bundle, stage)
        environment_unresolved = stage_result.get("failure_class") in {
            "container_start_failure", "execution_timeout_unresolved"}
        if not environment_unresolved:
            belt.complete(
                assignment, passed=stage_result["verified"],
                artifact_sha256=stage_result["artifact_sha256"]
                if stage_result["verified"] else None,
            )
        records.append({
            "stage": stage,
            "provider_metadata_sha256": sha256(metadata_path),
            "stage_report_sha256": sha256(
                bundle / "dag_output" / stage / "stage_report.json"
            ),
            "verified": stage_result["verified"],
        })
        if not stage_result["verified"]:
            break
    output = {
        **preflight, "status": "exploratory_real_llm_dag_feasibility_completed",
        "llm_calls": len(records), "job_outcome": "ENVIRONMENT_UNRESOLVED"
        if environment_unresolved else belt.job_outcomes()[case_id],
        "stages": records, "belt_event_hash": belt.engine.event_hash,
        "ability_rank_is_placeholder_for_one_model_harness": True,
        "not_a_policy_comparison": True,
    }
    (bundle / "dag_summary.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id", default="ADULT_P0")
    parser.add_argument("--model-slot", default="agent_2")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--check-container", action="store_true",
                        help="check locked Docker evaluator without calling MFEC")
    args = parser.parse_args()
    if args.check_container:
        if args.execute:
            parser.error("--check-container and --execute are mutually exclusive")
        print(json.dumps({
            "status": "container_ready_no_provider_call",
            "research_results": False,
            "container_preflight": preflight_container(),
        }, indent=2))
        return
    print(json.dumps(pilot(args.case_id, args.model_slot, execute=args.execute), indent=2))


if __name__ == "__main__":
    main()
