"""Bounded FastAPI Real-LLM repair diagnostic, not an allocation comparison.

Two gold-free, public-test-qualified bugs in one repository are each attempted
once by three frozen MFEC deployments. The model sees only selected buggy
source and one public failure; fixed source is never prompt-visible. Every
generated patch is checked in the isolated verifier, including replay.
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

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
OLD = V2 / "major_revision_v2_3"
sys.path[:0] = [str(OLD), str(V2 / "real_llm_pilot")]
from mfec_adapter import invoke  # noqa: E402
from repository_exact_edits_v3 import to_patch  # noqa: E402
from run_repository_first_attempt_v1 import INSTRUCTION  # noqa: E402
from run_repository_repair_pilot_v1 import execute_patch  # noqa: E402
from run_bugsinpy_preflight import environment  # noqa: E402

ROOT = HERE / "fastapi_llm_feasibility_v1"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"
RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_6/fastapi_llm_feasibility_v1")
GATE_RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_6/fastapi_candidates_v1")
PUBLIC_RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_6/fastapi_preflight_multinode_v1c")
CAPSULE = HERE / "fastapi_two_candidate_gates_capsule_v1.json"
GATE_LOCK = HERE / "fastapi_candidates_v1/lock.json"
GATE_LEDGER = HERE / "fastapi_candidates_v1/ledger.jsonl"
PROVIDER = V2 / "real_llm_pilot/config.mfec_main_frozen.json"
CASES = (
    ("fastapi_11", ("fastapi/openapi/utils.py", "fastapi/routing.py",
                    "fastapi/applications.py")),
    ("fastapi_8", ("fastapi/routing.py",)),
)
SLOTS = ("agent_1", "agent_2", "agent_3")
GENERATION = {"temperature": 0, "max_output_tokens": 16384,
              "timeout_seconds": 600}
TEST_TIMEOUT = 240


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def now():
    return datetime.now(timezone.utc).isoformat()


def candidate_sources(image: str, paths: tuple[str, ...]) -> dict[str, str]:
    code = ("import json;from pathlib import Path;"
            f"names={list(paths)!r};"
            "print(json.dumps({n:(Path('/candidate')/n).read_text(encoding='utf-8') "
            "for n in names},sort_keys=True))")
    result = subprocess.run(
        ["podman", "run", "--rm", "--network", "none", "--read-only",
         "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
         image, "python", "-c", code], capture_output=True, text=True,
        errors="replace", timeout=180, env=environment())
    if result.returncode != 0:
        raise RuntimeError("Buggy candidate source extraction failed")
    return json.loads(result.stdout)


def material():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    capsule = read(CAPSULE)
    if (capsule["status"] != "two_candidate_gates_audited_source_eligible_only"
            or capsule["provider_calls"] != 0 or
            capsule["lock_sha256"] != sha(GATE_LOCK) or
            capsule["ledger_sha256"] != sha(GATE_LEDGER)):
        raise ValueError("Independent source gate drift")
    provider = read(PROVIDER)
    models = [{key: model[key] for key in ("slot", "model_id", "exact_version")}
              for model in provider["models"]]
    if tuple(row["slot"] for row in models) != SLOTS:
        raise ValueError("Model roster drift")
    cases = []
    prompts = {}
    for index, (case_id, paths) in enumerate(CASES):
        gate_dir = GATE_RAW / f"{index:02d}_{case_id}"
        public_dir = PUBLIC_RAW / f"{index:02d}_{case_id}"
        summary_path = gate_dir / "summary.json"
        summary = read(summary_path)
        audit_case = capsule["cases"][index]
        if (audit_case["case_id"] != case_id or
                audit_case["summary_sha256"] != sha(summary_path) or
                summary["status"] != "candidate_preflight_passed"):
            raise ValueError("Candidate case gate drift")
        source_map = json.loads(read(gate_dir / "candidate_source_hashes.json")[
            "stdout"])
        sources = candidate_sources(summary["images"]["candidate"], paths)
        for path in paths:
            relative = path.removeprefix("fastapi/")
            if digest(sources[path].encode("utf-8")) != source_map[relative]:
                raise ValueError("Candidate source hash drift")
        visible_record = read(public_dir / "preflight_record.json")
        visible_nodes = visible_record["public_test_nodes"]
        if len(visible_nodes) != len(summary["visible"]):
            raise ValueError("Visible test count drift")
        first_execution = public_dir / "buggy/node_00/execution.json"
        if sha(first_execution) != visible_record["test_outcomes"]["buggy"][0][
                "execution_sha256"]:
            raise ValueError("Public failure evidence drift")
        # Public failure and source-file rule were chosen before these calls.
        failure = read(first_execution)["stdout"][-8000:]
        context = {"case_id": case_id, "allowed_source_files": sources,
                   "public_visible_nodes": visible_nodes,
                   "first_visible_failure_tail": failure,
                   "repair_scope": "Only the listed buggy production files may be edited."}
        prompt = INSTRUCTION + json.dumps(context, ensure_ascii=False)
        prompts[case_id] = prompt
        cases.append({"case_id": case_id,
                      "source_selection_rule": (
                          "fastapi_11: package files appearing in public buggy "
                          "tracebacks; fastapi_8: routing.py containing APIRoute "
                          "named by the public failure"),
                      "allowed_files": list(paths),
                      "source_sha256": {p: digest(s.encode("utf-8"))
                                        for p, s in sources.items()},
                      "prompt_sha256": digest(prompt.encode("utf-8")),
                      "first_visible_execution_sha256": sha(first_execution),
                      "candidate_summary_sha256": sha(summary_path),
                      "candidate_image": summary["images"]["candidate"],
                      "verifier_image": summary["images"]["verifier"],
                      "visible_nodes": visible_nodes,
                      "regression_nodes": summary["public_regression_nodeids"]})
    stable = {
        "status": "v2_6_fastapi_bounded_repair_diagnostic_frozen",
        "research_results": False, "allocation_comparison": False,
        "independent_repository_projects": 1,
        "not_main_12_repository_cohort": True,
        "claim_scope": "First-attempt repository repair feasibility on two FastAPI bugs; descriptive only",
        "model_slots": list(SLOTS), "models": models, "cases": cases,
        "planned_provider_calls": 6, "one_call_per_case_model": True,
        "no_automatic_retry_after_request_marker": True,
        "generation": GENERATION, "test_timeout_seconds": TEST_TIMEOUT,
        "provider_config_sha256": sha(PROVIDER),
        "source_capsule_sha256": sha(CAPSULE),
        "runner_sha256": sha(Path(__file__)),
        "adapter_sha256": sha(V2 / "real_llm_pilot/mfec_adapter.py"),
        "exact_edits_sha256": sha(OLD / "repository_exact_edits_v3.py"),
        "patch_verifier_sha256": sha(OLD / "run_repository_repair_pilot_v1.py"),
        "cost_rule": "Monetary cost unknown unless every response has reconciled billed currency and amount",
    }
    return stable, prompts


def freeze():
    stable, prompts = material()
    if LOCK.exists():
        old = read(LOCK)
        if any(old.get(key) != value for key, value in stable.items()):
            raise ValueError("Frozen diagnostic lock drift")
        for case_id, prompt in prompts.items():
            if sha(RAW / case_id / "prompt.txt") != digest(prompt.encode("utf-8")):
                raise ValueError("Frozen diagnostic prompt drift")
        return old
    if ROOT.exists() or RAW.exists():
        raise FileExistsError("Partial diagnostic freeze root; inspect, do not overwrite")
    ROOT.mkdir()
    RAW.mkdir(parents=True)
    for case_id, prompt in prompts.items():
        case_dir = RAW / case_id
        case_dir.mkdir()
        with (case_dir / "prompt.txt").open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(prompt)
    lock = {**stable, "created_at_utc": now()}
    save_new(LOCK, lock)
    return lock


def check_patch(job: Path, case: dict, patch: Path):
    baseline = {"images": {"verifier": case["verifier_image"]}}
    contract = {"allowed_files": case["allowed_files"]}
    rows = []
    for label, nodes in (("visible", case["visible_nodes"]),
                         ("regression", case["regression_nodes"]),
                         ("replay_visible", case["visible_nodes"]),
                         ("replay_regression", case["regression_nodes"])):
        result = execute_patch(patch, contract, baseline, label, nodes,
                               TEST_TIMEOUT)
        dispositions = result["dispositions"]
        okay = (result["execution"]["return_code"] == 0 and
                not result["execution"].get("timeout") and
                len(dispositions) >= len(nodes) and
                set(dispositions.values()) == {"passed"})
        rows.append({"label": label, "okay": okay,
                     "return_code": result["execution"]["return_code"],
                     "timeout": bool(result["execution"].get("timeout")),
                     "dispositions": dispositions,
                     "xml_sha256": result["xml_sha256"]})
        if not okay:
            break
    return rows


def run_next():
    lock = freeze()
    if not os.environ.get("MFEC_LITELLM_API_KEY"):
        raise ValueError("Process-only MFEC credential absent")
    provider = read(PROVIDER)
    pairs = [(case, model) for case in lock["cases"] for model in lock["models"]]
    for case, model in pairs:
        job = RAW / case["case_id"] / model["slot"]
        if job.exists():
            if not (job / "summary.json").exists():
                raise FileExistsError("Started request is unresolved; no blind retry")
            continue
        job.mkdir()
        save_new(job / "request_started.json", {
            "case_id": case["case_id"], "model_slot": model["slot"],
            "model_id": model["model_id"], "lock_sha256": sha(LOCK),
            "prompt_sha256": case["prompt_sha256"],
            "started_at_utc": now(), "automatic_retry": False})
        print(json.dumps({"event": "request_started", "case_id": case["case_id"],
                          "slot": model["slot"]}), flush=True)
        row = {"case_id": case["case_id"], "slot": model["slot"],
               "model_id": model["model_id"], "status": "PROVIDER_UNRESOLVED"}
        chosen = next(item for item in provider["models"]
                      if item["slot"] == model["slot"])
        try:
            response = invoke(
                model={**chosen, "base_url": provider["base_url"]},
                case={"prompt": (RAW / case["case_id"] / "prompt.txt").read_text(
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
                       response_sha256=sha(job / "response.txt"),
                       returned_model_version=response["exact_model_version"])
            if response["exact_model_version"] != model["exact_version"]:
                row["status"] = "PROVIDER_MAPPING_UNRESOLVED"
            elif response["finish_reason"] != "stop" or not content:
                row["status"] = "UNFINISHED_OR_EMPTY_OUTPUT"
            else:
                sources = candidate_sources(case["candidate_image"],
                                            tuple(case["allowed_files"]))
                if {p: digest(s.encode("utf-8")) for p, s in sources.items()} != case[
                        "source_sha256"]:
                    raise ValueError("Candidate source changed after provider call")
                try:
                    patch = to_patch(json.loads(content), sources,
                                     case["allowed_files"])
                except (ValueError, TypeError, KeyError) as error:
                    row.update(status="EXACT_EDITS_CONTRACT_FAILED",
                               error_type=type(error).__name__)
                else:
                    patch_path = job / "patch.diff"
                    patch_path.write_bytes(patch)
                    row["patch_sha256"] = sha(patch_path)
                    tests = check_patch(job, case, patch_path)
                    row["checks"] = tests
                    row["status"] = ("VERIFIED" if len(tests) == 4 and
                                     all(item["okay"] for item in tests) else
                                     "TEST_OR_REPLAY_FAILED")
        save_new(job / "summary.json", row)
        with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps({"case_id": case["case_id"],
                                     "slot": model["slot"], "status": row["status"],
                                     "summary_sha256": sha(job / "summary.json")},
                                    sort_keys=True) + "\n")
        print(json.dumps({"event": "attempt_complete", "case_id": case["case_id"],
                          "slot": model["slot"], "status": row["status"]}), flush=True)
        return row
    return {"status": "all_six_attempts_recorded_requires_independent_audit",
            "provider_calls_planned": 6}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run-next", action="store_true")
    parser.add_argument("--confirm-paid-diagnostic", action="store_true")
    args = parser.parse_args()
    if args.run_next and not args.confirm_paid_diagnostic:
        parser.error("--run-next needs --confirm-paid-diagnostic")
    result = run_next() if args.run_next else {
        "status": freeze()["status"], "lock_sha256": sha(LOCK),
        "provider_calls": 0}
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
