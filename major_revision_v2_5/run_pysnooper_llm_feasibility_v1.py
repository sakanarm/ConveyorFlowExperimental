"""Frozen PySnooper repair feasibility using three MFEC LLM deployments.

This is an exploratory real-LLM task/verification check, not an allocation arm.
The model sees only buggy source and one visible public test. The candidate
image has no fixed production source; all patch checks run in Podman.
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


HERE = Path(__file__).resolve().parent
V2 = HERE.parent
OLD = V2 / "major_revision_v2_3"
sys.path.insert(0, str(OLD))
sys.path.insert(0, str(V2 / "real_llm_pilot"))
from mfec_adapter import invoke  # noqa: E402
from repository_exact_edits_v3 import to_patch  # noqa: E402
from run_repository_first_attempt_v1 import INSTRUCTION  # noqa: E402
from run_repository_repair_pilot_v1 import execute_patch  # noqa: E402


ROOT = HERE / "results/v25_pysnooper_llm_feasibility_v1"
LOCK = ROOT / "lock.json"
PROVIDER = V2 / "real_llm_pilot/config.mfec_main_frozen.json"
GATE = HERE / "results/pysnooper_regression_v1c/lock.json"
GATE_RESULT = HERE / "results/pysnooper_regression_v1c/summary.json"
SOURCE = "pysnooper/pysnooper.py"
TEST = "tests/test_pysnooper.py"
GENERATION = {"temperature": 0, "max_output_tokens": 32768, "timeout_seconds": 720}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return digest(path.read_bytes())


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def podman_read(image: str, inner_path: str) -> str:
    response = subprocess.run(
        ["podman", "run", "--rm", "--network", "none", "--read-only",
         "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
         image, "cat", inner_path],
        capture_output=True, timeout=120, check=False,
    )
    if response.returncode:
        raise RuntimeError("Candidate source extraction failed: " + inner_path)
    return response.stdout.decode("utf-8")


def frozen_material() -> tuple[dict, str, dict]:
    gate, outcome, provider = read(GATE), read(GATE_RESULT), read(PROVIDER)
    if (gate["status"] != "v2_5_all_four_public_regressions_frozen_before_provider"
            or outcome["status"] != "candidate_preflight_passed"
            or outcome["active_public_regression_passes"] != 4
            or gate["visible_test"] != "tests/test_pysnooper.py::test_file_output"):
        raise ValueError("Pre-provider PySnooper gates are not satisfied")
    source = podman_read(gate["candidate_image_id"], "/candidate/" + SOURCE)
    if digest(source.encode()) != read(HERE / "results/pysnooper_candidate_v1b/PySnooper_3/summary.json")["candidate_audit"]["allowed_source_sha256"][SOURCE]:
        raise ValueError("Buggy source digest differs from candidate audit")
    test_text = podman_read(gate["verifier_image_id"], "/protected/" + TEST)
    nodes = [node for node in ast.walk(ast.parse(test_text))
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
             and node.name == "test_file_output"]
    if len(nodes) != 1:
        raise ValueError("Visible test function not uniquely located")
    lines = test_text.splitlines()
    visible = "\n".join(lines[nodes[0].lineno - 1:nodes[0].end_lineno])
    context = {"case_id": "PySnooper_3", "allowed_source_files": {SOURCE: source},
               "visible_test_source": visible,
               "visible_test_node": gate["visible_test"]}
    prompt = INSTRUCTION + json.dumps(context, ensure_ascii=False)
    models = [{key: model[key] for key in ("slot", "model_id", "exact_version")}
              for model in provider["models"]]
    stable = {
        "status": "frozen_before_pysnooper_paid_calls",
        "research_results": False,
        "exploratory_repository_repair_feasibility": True,
        "not_allocation_comparison": True,
        "not_independent_repository_replicates": True,
        "case_id": "PySnooper_3", "models": models,
        "planned_provider_calls": 3, "one_call_per_model": True,
        "no_retry_after_request_started": True,
        "generation": GENERATION,
        "provider_config_sha256": sha(PROVIDER),
        "gate_lock_sha256": sha(GATE), "gate_result_sha256": sha(GATE_RESULT),
        "prompt_sha256": digest(prompt.encode("utf-8")),
        "buggy_source_sha256": digest(source.encode("utf-8")),
        "visible_test_source_sha256": digest(visible.encode("utf-8")),
        "runner_sha256": sha(Path(__file__)),
        "adapter_sha256": sha(V2 / "real_llm_pilot/mfec_adapter.py"),
        "exact_edits_sha256": sha(OLD / "repository_exact_edits_v3.py"),
        "patch_guard_sha256": sha(OLD / "repository_patch_guard_v1.py"),
    }
    return stable, prompt, context


def freeze() -> tuple[dict, dict]:
    if sys.platform != "linux" or os.geteuid() != 0:
        raise ValueError("Linux rootful Podman required")
    stable, prompt, context = frozen_material()
    if LOCK.exists():
        locked = read(LOCK)
        if any(locked.get(key) != val for key, val in stable.items()):
            raise ValueError("Frozen instrument drift")
        if sha(ROOT / "prompt.txt") != stable["prompt_sha256"]:
            raise ValueError("Frozen prompt changed")
        return locked, context
    if ROOT.exists():
        raise FileExistsError("Output root exists without lock")
    ROOT.mkdir(parents=True)
    with (ROOT / "prompt.txt").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(prompt)
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked, context


def run() -> None:
    lock, context = freeze()
    secret = sys.stdin.readline().strip()
    if not secret or len(secret) > 4096:
        raise ValueError("API credential required through stdin")
    os.environ["MFEC_LITELLM_API_KEY"] = secret
    provider = read(PROVIDER)
    gate = read(GATE)
    expected_regression = read(GATE_RESULT)["reports"]["buggy_regression"]["dispositions"]
    expected_visible = {next(iter(read(GATE_RESULT)["reports"]["visible"]["dispositions"])): "passed"}
    for model in lock["models"]:
        slot = model["slot"]
        job = ROOT / slot
        if job.exists():
            raise FileExistsError("Started model pair exists; no automatic retry: " + slot)
        job.mkdir()
        save_new(job / "request_started.json", {
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_id": model["model_id"], "slot": slot,
            "lock_sha256": sha(LOCK), "prompt_sha256": lock["prompt_sha256"],
        })
        print(json.dumps({"event": "request_started", "slot": slot}), flush=True)
        row = {"slot": slot, "model_id": model["model_id"], "status": "PROVIDER_UNRESOLVED"}
        try:
            response = invoke(
                model={**next(item for item in provider["models"] if item["slot"] == slot),
                       "base_url": provider["base_url"]},
                case={"prompt": (ROOT / "prompt.txt").read_text(encoding="utf-8")},
                generation=GENERATION,
            )
        except Exception as error:
            row["provider_error_type"] = type(error).__name__
            row["http_status"] = getattr(error, "code", None)
            row["billable_outcome_unknown"] = True
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
                   input_tokens=response["input_tokens"], output_tokens=response["output_tokens"],
                   response_cost=response.get("response_cost"),
                   response_sha256=sha(job / "response.txt"),
                   returned_model_version=response["exact_model_version"])
        if response["exact_model_version"] != model["exact_version"]:
            row["status"] = "PROVIDER_MAPPING_UNRESOLVED"
        elif response["finish_reason"] != "stop" or not content:
            row["status"] = "UNFINISHED_OR_EMPTY_OUTPUT"
        else:
            try:
                patch = to_patch(json.loads(content), context["allowed_source_files"], [SOURCE])
            except (ValueError, TypeError, KeyError) as error:
                row.update(status="EXACT_EDITS_CONTRACT_FAILED", error_type=type(error).__name__)
            else:
                (job / "patch.diff").write_bytes(patch)
                row["patch_sha256"] = sha(job / "patch.diff")
                case = {"allowed_files": [SOURCE]}
                baseline = {"images": {"verifier": gate["verifier_image_id"]}}
                row["status"] = "VERIFIED"
                for label, nodes, expected in (
                    ("visible", [gate["visible_test"]], expected_visible),
                    ("regression", gate["non_visible_public_nodes"], expected_regression),
                    ("replay_visible", [gate["visible_test"]], expected_visible),
                    ("replay_regression", gate["non_visible_public_nodes"], expected_regression),
                ):
                    result = execute_patch(job / "patch.diff", case, baseline,
                                           label, nodes, 180)
                    row[label] = {
                        "return_code": result["execution"]["return_code"],
                        "timeout": bool(result["execution"].get("timeout")),
                        "dispositions": result["dispositions"],
                        "xml_sha256": result["xml_sha256"],
                    }
                    if row[label]["timeout"] or row[label]["return_code"] in (125, 126, 127):
                        row["status"] = "VERIFIER_ENVIRONMENT_UNRESOLVED"
                        break
                    if row[label]["return_code"] != 0 or row[label]["dispositions"] != expected:
                        row["status"] = "VISIBLE_TEST_FAILED" if label == "visible" else "PUBLIC_REGRESSION_OR_REPLAY_FAILED"
                        break
        save_new(job / "summary.json", row)
        print(json.dumps({"event": "pair_finished", "slot": slot,
                          "status": row["status"]}), flush=True)
        if row["status"] in ("PROVIDER_MAPPING_UNRESOLVED", "VERIFIER_ENVIRONMENT_UNRESOLVED"):
            break


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action", choices=("freeze", "execute"))
    args = cli.parse_args()
    if args.action == "freeze":
        frozen, _ = freeze()
        print(json.dumps({"status": frozen["status"], "calls_planned": 3,
                          "research_results": False}))
    else:
        run()
