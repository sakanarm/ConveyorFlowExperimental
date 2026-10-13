"""Exploratory prompt amendment after the six-attempt FastAPI diagnostic.

The first diagnostic omitted the visible test source. This separate version
adds only public visible tests and reduces generation budget for one frozen
deployment. It is adaptive, not a first-attempt or allocation result, and
must not be pooled with the original six attempts.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import run_fastapi_llm_feasibility_v1 as prior

HERE = Path(__file__).resolve().parent
ROOT = HERE / "fastapi_llm_prompt_amendment_v1"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"
RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_6/fastapi_llm_prompt_amendment_v1")
PUBLIC = Path("/mnt/d/ConveyorFlowRuntime/v2_6/fastapi_preflight_multinode_v1c")
GENERATION = {"temperature": 0, "max_output_tokens": 4096,
              "timeout_seconds": 600}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def public_text(image, path):
    run = subprocess.run(
        ["podman", "run", "--rm", "--network", "none", "--read-only",
         "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
         image, "cat", "/protected/" + path],
        capture_output=True, text=True, errors="replace", timeout=180,
        env=prior.environment())
    if run.returncode:
        raise RuntimeError("Public visible test extraction failed")
    return run.stdout


def material():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    original = read(prior.LOCK)
    audited = read(HERE / "fastapi_llm_feasibility_v1/audit_capsule_v1.json")
    if (audited["status"] != "six_diagnostic_attempts_independently_audited"
            or audited["verified_repairs"] != 0 or
            audited["lock_sha256"] != sha(prior.LOCK) or
            audited["ledger_sha256"] != sha(prior.LEDGER)):
        raise ValueError("Prior diagnostic outcome or audit drift")
    model = next(row for row in original["models"] if row["slot"] == "agent_2")
    cases = []
    prompts = {}
    for index, case in enumerate(original["cases"]):
        case_id = case["case_id"]
        source = prior.candidate_sources(case["candidate_image"],
                                         tuple(case["allowed_files"]))
        if {p: digest(s.encode("utf-8")) for p, s in source.items()} != case[
                "source_sha256"]:
            raise ValueError("Original buggy source drift")
        record = read(PUBLIC / f"{index:02d}_{case_id}/preflight_record.json")
        tests = {path: public_text(case["verifier_image"], path)
                 for path in record["public_test_files"]}
        failure = read(PUBLIC / f"{index:02d}_{case_id}/buggy/node_00/execution.json")[
            "stdout"][-6000:]
        context = {"case_id": case_id, "allowed_source_files": source,
                   "visible_public_test_files": tests,
                   "visible_failure_tail": failure,
                   "required_visible_nodes": case["visible_nodes"],
                   "instruction": "Preserve the existing API and make the visible public tests pass with a minimal production-only repair."}
        prompt = prior.INSTRUCTION + json.dumps(context, ensure_ascii=False)
        prompts[case_id] = prompt
        cases.append({"case_id": case_id,
                      "prompt_sha256": digest(prompt.encode("utf-8")),
                      "visible_test_source_sha256": {p: digest(t.encode("utf-8"))
                                                     for p, t in tests.items()},
                      "original_candidate_summary_sha256":
                          case["candidate_summary_sha256"]})
    stable = {"status": "v2_6_fastapi_adaptive_prompt_amendment_frozen",
              "exploratory_adaptive_follow_up": True,
              "not_independent_first_attempt": True,
              "not_allocation_comparison": True,
              "not_pool_with_six_prior_attempts": True,
              "amendment": "Include all declared public visible test files in the prompt and use a 4096-output-token cap",
              "cases": cases, "model": model,
              "planned_provider_calls": 2,
              "one_call_per_case_in_this_version": True,
              "case_order": [row["case_id"] for row in cases],
              "generation": GENERATION,
              "prior_lock_sha256": sha(prior.LOCK),
              "prior_audit_sha256": sha(HERE / "fastapi_llm_feasibility_v1/audit_capsule_v1.json"),
              "provider_config_sha256": sha(prior.PROVIDER),
              "runner_sha256": sha(Path(__file__)),
              "provider_calls_before_freeze": 0}
    return stable, prompts


def freeze():
    stable, prompts = material()
    if LOCK.exists():
        old = read(LOCK)
        if any(old.get(k) != v for k, v in stable.items()):
            raise ValueError("Amendment lock drift")
        for case_id, prompt in prompts.items():
            if sha(RAW / case_id / "prompt.txt") != digest(prompt.encode("utf-8")):
                raise ValueError("Amended prompt drift")
        return old
    if ROOT.exists() or RAW.exists():
        raise FileExistsError("Partial amendment root; inspect before continuation")
    ROOT.mkdir()
    RAW.mkdir(parents=True)
    for case_id, prompt in prompts.items():
        folder = RAW / case_id
        folder.mkdir()
        with (folder / "prompt.txt").open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(prompt)
    lock = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, lock)
    return lock


def run_next():
    lock = freeze()
    if not os.environ.get("MFEC_LITELLM_API_KEY"):
        raise ValueError("Process-only MFEC key absent")
    provider = read(prior.PROVIDER)
    chosen = next(row for row in provider["models"] if row["slot"] == "agent_2")
    original = read(prior.LOCK)
    for amendment_case, case in zip(lock["cases"], original["cases"]):
        case_id = amendment_case["case_id"]
        job = RAW / case_id / "agent_2"
        if job.exists():
            if not (job / "summary.json").exists():
                raise FileExistsError("Started amended request unresolved; no retry")
            continue
        job.mkdir()
        save_new(job / "request_started.json", {
            "case_id": case_id, "slot": "agent_2",
            "lock_sha256": sha(LOCK),
            "prompt_sha256": amendment_case["prompt_sha256"],
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "automatic_retry": False})
        print(json.dumps({"event": "request_started", "case_id": case_id}), flush=True)
        row = {"case_id": case_id, "slot": "agent_2",
               "status": "PROVIDER_UNRESOLVED"}
        try:
            response = prior.invoke(
                model={**chosen, "base_url": provider["base_url"]},
                case={"prompt": (RAW / case_id / "prompt.txt").read_text(
                    encoding="utf-8")}, generation=GENERATION)
        except Exception as error:
            row.update(provider_error_type=type(error).__name__,
                       http_status=getattr(error, "code", None),
                       billable_outcome_unknown=True)
        else:
            content = str(response.pop("content"))
            (job / "response.txt").write_text(content, encoding="utf-8")
            save_new(job / "provider.json", response)
            row.update(provider_request_id=response["provider_request_id"],
                       input_tokens=response["input_tokens"],
                       output_tokens=response["output_tokens"],
                       response_cost=response.get("response_cost"),
                       returned_model_version=response["exact_model_version"],
                       response_sha256=sha(job / "response.txt"))
            if response["exact_model_version"] != lock["model"]["exact_version"]:
                row["status"] = "PROVIDER_MAPPING_UNRESOLVED"
            elif response["finish_reason"] != "stop" or not content:
                row["status"] = "UNFINISHED_OR_EMPTY_OUTPUT"
            else:
                source = prior.candidate_sources(case["candidate_image"],
                                                 tuple(case["allowed_files"]))
                try:
                    patch = prior.to_patch(json.loads(content), source,
                                           case["allowed_files"])
                except (ValueError, TypeError, KeyError) as error:
                    row.update(status="EXACT_EDITS_CONTRACT_FAILED",
                               error_type=type(error).__name__)
                else:
                    patch_path = job / "patch.diff"
                    patch_path.write_bytes(patch)
                    row["patch_sha256"] = sha(patch_path)
                    checks = prior.check_patch(job, case, patch_path)
                    row["checks"] = checks
                    row["status"] = ("VERIFIED" if len(checks) == 4 and
                                     all(check["okay"] for check in checks) else
                                     "TEST_OR_REPLAY_FAILED")
        save_new(job / "summary.json", row)
        with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps({"case_id": case_id, "slot": "agent_2",
                                     "status": row["status"],
                                     "summary_sha256": sha(job / "summary.json")},
                                    sort_keys=True) + "\n")
        print(json.dumps({"event": "attempt_complete", "case_id": case_id,
                          "status": row["status"]}), flush=True)
        return row
    return {"status": "two_amended_attempts_recorded_requires_audit"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run-next", action="store_true")
    parser.add_argument("--confirm-paid-exploratory", action="store_true")
    args = parser.parse_args()
    if args.run_next and not args.confirm_paid_exploratory:
        parser.error("--run-next requires --confirm-paid-exploratory")
    result = run_next() if args.run_next else {
        "status": freeze()["status"], "lock_sha256": sha(LOCK),
        "provider_calls": 0}
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
