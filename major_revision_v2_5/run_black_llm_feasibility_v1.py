"""One-call-per-model Black repair feasibility; NOT an allocation comparison.

This extension checks a second independent repository's real-LLM interface.
Only buggy source excerpts and a visible public test enter the prompt. The
complete buggy file stays in the local exact-edits guard; fixed source stays
only in the verifier. No paid call is repeated after a request marker exists.
"""

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import audit_black_candidate_v1 as gate_audit

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "major_revision_v2_3"
V2 = HERE.parent
sys.path[:0] = [str(OLD), str(V2 / "real_llm_pilot")]
from mfec_adapter import invoke  # noqa: E402
from repository_exact_edits_v3 import to_patch  # noqa: E402
from run_repository_first_attempt_v1 import INSTRUCTION  # noqa: E402
from run_repository_repair_pilot_v1 import execute_patch  # noqa: E402

ROOT = HERE / "results/v25_black_llm_feasibility_v1"
LOCK = ROOT / "lock.json"
PROVIDER = V2 / "real_llm_pilot/config.mfec_main_frozen.json"
BASELINE = HERE / "results/black_candidate_v1/black_3/summary.json"
BASELINE_LOCK = HERE / "results/black_candidate_v1/lock.json"
SOURCE = "black.py"
VISIBLE_FILE = "tests/test_black.py"
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


def podman_read(image, path):
    result = subprocess.run(["podman", "run", "--rm", "--network", "none",
                             "--read-only", "--cap-drop", "ALL",
                             "--security-opt", "no-new-privileges", image,
                             "cat", path], capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError("Candidate-visible source extraction failed")
    return result.stdout.decode("utf-8")


def function_source(source, name):
    nodes = [node for node in ast.walk(ast.parse(source))
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and
             node.name == name]
    if len(nodes) != 1:
        raise ValueError("Source function not uniquely located: " + name)
    node = nodes[0]
    lines = source.splitlines()
    return {"first_line": node.lineno, "text": "\n".join(lines[node.lineno-1:node.end_lineno])}


def frozen_material():
    if gate_audit.audit()["status"] != "independent_candidate_audit_passed":
        raise ValueError("Independent Black pre-provider gate failed")
    baseline, gate, provider = read(BASELINE), read(BASELINE_LOCK), read(PROVIDER)
    source = podman_read(baseline["images"]["candidate"], "/candidate/black.py")
    if hashlib.sha256(source.encode()).hexdigest() != baseline[
            "candidate_audit"]["allowed_source_sha256"][SOURCE]:
        raise ValueError("Buggy Black source digest mismatch")
    tests = podman_read(baseline["images"]["verifier"], "/protected/" + VISIBLE_FILE)
    visible = function_source(tests, "test_invalid_config_return_code")
    excerpt = function_source(source, "read_pyproject_toml")
    context = {"case_id": "black_3", "allowed_paths": [SOURCE],
               "buggy_source_ranges": [{"path": SOURCE, **excerpt}],
               "visible_test_node": gate["case"]["visible_test"],
               "visible_test_source": visible["text"]}
    prompt = INSTRUCTION + json.dumps(context, ensure_ascii=False)
    models = [{key: row[key] for key in ("slot", "model_id", "exact_version")}
              for row in provider["models"]]
    stable = {"status": "frozen_before_black_paid_calls", "research_results": False,
              "exploratory_repository_repair_feasibility": True,
              "not_allocation_comparison": True,
              "one_independent_repository_source": True,
              "case_id": "black_3", "models": models,
              "planned_provider_calls": len(models), "one_call_per_model": True,
              "no_retry_after_request_started": True, "generation": GENERATION,
              "provider_config_sha256": sha(PROVIDER),
              "baseline_sha256": sha(BASELINE), "baseline_lock_sha256": sha(BASELINE_LOCK),
              "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
              "buggy_source_sha256": hashlib.sha256(source.encode()).hexdigest(),
              "visible_test_source_sha256": hashlib.sha256(visible["text"].encode()).hexdigest(),
              "runner_sha256": sha(__file__),
              "adapter_sha256": sha(V2 / "real_llm_pilot/mfec_adapter.py"),
              "exact_edits_sha256": sha(OLD / "repository_exact_edits_v3.py")}
    return stable, prompt, source


def freeze():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    stable, prompt, source = frozen_material()
    if LOCK.exists():
        locked = read(LOCK)
        if any(locked.get(key) != value for key, value in stable.items()) or sha(
                ROOT / "prompt.txt") != stable["prompt_sha256"]:
            raise ValueError("Black paid-instrument lock drift")
        return locked, source
    if ROOT.exists():
        raise FileExistsError("Unfrozen Black output root exists")
    ROOT.mkdir(parents=True)
    (ROOT / "prompt.txt").write_text(prompt, encoding="utf-8")
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked, source


def execute():
    lock, source = freeze()
    secret = sys.stdin.readline().strip()
    if not secret or len(secret) > 4096:
        raise ValueError("Process-only MFEC credential required on stdin")
    os.environ["MFEC_LITELLM_API_KEY"] = secret
    provider, baseline, gate = read(PROVIDER), read(BASELINE), read(BASELINE_LOCK)
    visible = gate["case"]["visible_test"]
    nodes = baseline["selected_regression_nodes"]
    expected_regressions = baseline["reports"]["buggy_regressions"]["dispositions"]
    expected_visible = baseline["reports"]["visible_fixed"]["dispositions"]
    for model in lock["models"]:
        slot = model["slot"]
        job = ROOT / slot
        if job.exists():
            raise FileExistsError("Started model attempt retained: " + slot)
        job.mkdir()
        save_new(job / "request_started.json", {"slot": slot, "model_id": model["model_id"],
                 "lock_sha256": sha(LOCK), "prompt_sha256": lock["prompt_sha256"],
                 "started_at_utc": datetime.now(timezone.utc).isoformat()})
        print(json.dumps({"event": "request_started", "slot": slot}), flush=True)
        row = {"slot": slot, "model_id": model["model_id"], "status": "PROVIDER_UNRESOLVED"}
        try:
            response = invoke(model={**next(item for item in provider["models"]
                                               if item["slot"] == slot),
                                     "base_url": provider["base_url"]},
                              case={"prompt": (ROOT / "prompt.txt").read_text(encoding="utf-8")},
                              generation=GENERATION)
        except Exception as error:
            row.update(provider_error_type=type(error).__name__,
                       http_status=getattr(error, "code", None), billable_outcome_unknown=True)
            save_new(job / "summary.json", row)
            print(json.dumps({"event": "pair_finished", "slot": slot,
                              "status": row["status"]}), flush=True)
            if row["http_status"] in (401, 403):
                break
            continue
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
            try:
                patch = to_patch(json.loads(content), {SOURCE: source}, [SOURCE])
            except (ValueError, TypeError, KeyError) as error:
                row.update(status="EXACT_EDITS_CONTRACT_FAILED", error_type=type(error).__name__)
            else:
                (job / "patch.diff").write_bytes(patch)
                row["patch_sha256"] = sha(job / "patch.diff")
                row["status"] = "VERIFIED"
                for label, subset, expected in (
                    ("visible", [visible], expected_visible),
                    ("regression", nodes, expected_regressions),
                    ("replay_visible", [visible], expected_visible),
                    ("replay_regression", nodes, expected_regressions),
                ):
                    result = execute_patch(job / "patch.diff", {"allowed_files": [SOURCE]},
                                           baseline, label, subset, 240)
                    row[label] = {"return_code": result["execution"]["return_code"],
                                  "timeout": bool(result["execution"].get("timeout")),
                                  "dispositions": result["dispositions"],
                                  "xml_sha256": result["xml_sha256"]}
                    if row[label]["timeout"] or row[label]["return_code"] in (125, 126, 127):
                        row["status"] = "VERIFIER_ENVIRONMENT_UNRESOLVED"
                        break
                    if row[label]["return_code"] != 0 or row[label]["dispositions"] != expected:
                        row["status"] = ("VISIBLE_TEST_FAILED" if label == "visible"
                                         else "PUBLIC_REGRESSION_OR_REPLAY_FAILED")
                        break
        save_new(job / "summary.json", row)
        print(json.dumps({"event": "pair_finished", "slot": slot,
                          "status": row["status"]}), flush=True)
        if row["status"] in ("PROVIDER_MAPPING_UNRESOLVED", "VERIFIER_ENVIRONMENT_UNRESOLVED"):
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "execute"))
    arguments = parser.parse_args()
    if arguments.action == "freeze":
        locked, _ = freeze()
        print(json.dumps({"status": locked["status"],
                          "planned_provider_calls": locked["planned_provider_calls"],
                          "research_results": False}), flush=True)
    else:
        execute()
