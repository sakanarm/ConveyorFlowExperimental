"""One-call output-budget diagnostic on an already exposed FastAPI case.

This is instrument calibration only, not a new case, independent sample,
allocation result, model-rank update, or v2.6 main-cohort observation.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

import run_fastapi_llm_feasibility_v1 as prior
from mfec_adapter import invoke
from repository_exact_edits_v3 import to_patch

HERE = Path(__file__).resolve().parent
ROOT = HERE / "repair_output_budget_pilot_v1"
LOCK = ROOT / "lock.json"
RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_6/repair_output_budget_pilot_v1")
PROMPT = Path(
    "/mnt/d/ConveyorFlowRuntime/v2_6/fastapi_llm_prompt_amendment_v1/fastapi_8/prompt.txt"
)
PRIOR_LOCK = HERE / "fastapi_llm_prompt_amendment_v1/lock.json"
GENERATION = {"temperature": 0, "max_output_tokens": 32768,
              "timeout_seconds": 720}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def freeze():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    earlier = read(PRIOR_LOCK)
    case = read(prior.LOCK)["cases"][1]
    if (case["case_id"] != "fastapi_8" or
            sha(PROMPT) != earlier["cases"][1]["prompt_sha256"]):
        raise ValueError("Exposed pilot prompt/case drift")
    model = next(row for row in read(prior.PROVIDER)["models"]
                 if row["slot"] == "agent_1")
    stable = {
        "status": "one_call_exposed_case_output_budget_instrument_pilot_frozen",
        "not_main": True,
        "not_first_attempt": True,
        "not_allocation_comparison": True,
        "never_pool_with_main_or_prior_attempts": True,
        "case_id": "fastapi_8",
        "model": {k: model[k] for k in ("slot", "model_id", "exact_version")},
        "generation": GENERATION,
        "planned_provider_calls": 1,
        "no_automatic_retry": True,
        "prior_exposure_sha256": sha(PRIOR_LOCK),
        "case_lock_sha256": sha(prior.LOCK),
        "prompt_sha256": sha(PROMPT),
        "provider_config_sha256": sha(prior.PROVIDER),
        "runner_sha256": sha(__file__),
        "adapter_sha256": sha(HERE.parent / "real_llm_pilot/mfec_adapter.py"),
        "verifier_sha256": sha(prior.OLD / "run_repository_repair_pilot_v1.py"),
    }
    if LOCK.exists():
        old = read(LOCK)
        if any(old.get(key) != value for key, value in stable.items()):
            raise ValueError("Pilot lock drift")
        if sha(RAW / "prompt.txt") != stable["prompt_sha256"]:
            raise ValueError("Pilot prompt copy drift")
        return old
    if ROOT.exists() or RAW.exists():
        raise FileExistsError("Partial pilot root; inspect before continuing")
    ROOT.mkdir()
    RAW.mkdir()
    (RAW / "prompt.txt").write_bytes(PROMPT.read_bytes())
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def run():
    lock = freeze()
    if not os.environ.get("MFEC_LITELLM_API_KEY"):
        raise ValueError("Process-only MFEC credential absent")
    if (RAW / "request_started.json").exists():
        raise FileExistsError("Provider request already started; no retry")
    model = next(row for row in read(prior.PROVIDER)["models"]
                 if row["slot"] == lock["model"]["slot"])
    case = read(prior.LOCK)["cases"][1]
    save_new(RAW / "request_started.json", {
        "lock_sha256": sha(LOCK), "prompt_sha256": lock["prompt_sha256"],
        "model_slot": model["slot"], "started_at_utc":
        datetime.now(timezone.utc).isoformat(), "automatic_retry": False})
    print(json.dumps({"event": "request_started", "case_id": "fastapi_8",
                      "model_slot": model["slot"]}), flush=True)
    result = {"status": "PROVIDER_UNRESOLVED", "case_id": "fastapi_8"}
    try:
        response = invoke(
            model={**model, "base_url": read(prior.PROVIDER)["base_url"]},
            case={"prompt": (RAW / "prompt.txt").read_text(encoding="utf-8")},
            generation=lock["generation"])
    except Exception as error:
        result.update(error_type=type(error).__name__,
                      http_status=getattr(error, "code", None),
                      billable_outcome_unknown=True)
    else:
        content = str(response.pop("content"))
        (RAW / "response.txt").write_text(content, encoding="utf-8")
        save_new(RAW / "provider.json", response)
        result.update(
            provider_request_id=response["provider_request_id"],
            finish_reason=response["finish_reason"],
            input_tokens=response["input_tokens"],
            output_tokens=response["output_tokens"],
            response_cost_units_currency_unverified=response.get("response_cost"),
            response_sha256=sha(RAW / "response.txt"))
        if response["exact_model_version"] != model["exact_version"]:
            result["status"] = "PROVIDER_MAPPING_UNRESOLVED"
        elif response["finish_reason"] != "stop" or not content:
            result["status"] = "UNFINISHED_OR_EMPTY_OUTPUT"
        else:
            sources = prior.candidate_sources(case["candidate_image"],
                                              tuple(case["allowed_files"]))
            if {p: hashlib.sha256(value.encode("utf-8")).hexdigest()
                    for p, value in sources.items()} != case["source_sha256"]:
                raise ValueError("Buggy source drift after provider request")
            try:
                patch = to_patch(json.loads(content), sources,
                                 case["allowed_files"])
            except (ValueError, TypeError, KeyError) as error:
                result.update(status="EXACT_EDITS_CONTRACT_FAILED",
                              error_type=type(error).__name__)
            else:
                patch_path = RAW / "patch.diff"
                patch_path.write_bytes(patch)
                result["patch_sha256"] = sha(patch_path)
                checks = prior.check_patch(RAW, case, patch_path)
                result["checks"] = checks
                result["status"] = ("VERIFIED" if len(checks) == 4 and
                                    all(row["okay"] for row in checks) else
                                    "TEST_OR_REPLAY_FAILED")
    save_new(RAW / "summary.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--run", action="store_true")
    parser.add_argument("--confirm-paid-instrument-pilot", action="store_true")
    args = parser.parse_args()
    if args.run and not args.confirm_paid_instrument_pilot:
        parser.error("Explicit paid instrument pilot confirmation required")
    output = run() if args.run else {"status": freeze()["status"],
                                     "provider_calls": 0, "lock_sha256": sha(LOCK)}
    print(json.dumps(output, sort_keys=True), flush=True)
