"""One-shot exact-edits repository executor for v2.5 paired arms."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

import freeze_paired_extension_v1 as design
import run_black_llm_feasibility_v1 as black_source

sys.path[:0] = [str(design.OLD), str(design.V2 / "real_llm_pilot")]
from mfec_adapter import invoke  # noqa: E402
from repository_exact_edits_v3 import to_patch  # noqa: E402
from run_repository_first_attempt_v1 import INSTRUCTION  # noqa: E402
from run_repository_repair_pilot_v1 import execute_patch  # noqa: E402


def material(case_id):
    if case_id == "black_3":
        baseline = design.read(design.BLACK_GATE)
        gate = design.read(design.HERE / "results/black_candidate_v1/lock.json")
        source = black_source.podman_read(baseline["images"]["candidate"],
                                         "/candidate/black.py")
        if design.sha(design.BLACK_GATE) != design.read(design.LOCK)[
                "dependencies_sha256"]["black_candidate"]:
            raise ValueError("Black verifier baseline changed")
        return {"source_path": "black.py", "source": source,
                "prompt": design.BLACK_PROMPT,
                "baseline": baseline,
                "visible": gate["case"]["visible_test"],
                "regression_nodes": baseline["selected_regression_nodes"],
                "expected_visible": baseline["reports"]["visible_fixed"]["dispositions"],
                "expected_regression": baseline["reports"]["buggy_regressions"]["dispositions"]}
    if case_id == "PySnooper_3":
        gate = design.read(design.HERE / "results/pysnooper_regression_v1c/lock.json")
        baseline = design.read(design.PY_GATE)
        prompt = design.PY_PROMPT.read_text(encoding="utf-8")
        if not prompt.startswith(INSTRUCTION):
            raise ValueError("PySnooper prompt instruction drift")
        context = json.loads(prompt[len(INSTRUCTION):])
        source_path = "pysnooper/pysnooper.py"
        source = context["allowed_source_files"][source_path]
        return {"source_path": source_path, "source": source,
                "prompt": design.PY_PROMPT,
                "baseline": {"images": {"verifier": gate["verifier_image_id"]}},
                "visible": gate["visible_test"],
                "regression_nodes": gate["non_visible_public_nodes"],
                "expected_visible": {"tests.test_pysnooper::test_file_output": "passed"},
                "expected_regression": baseline["reports"]["buggy_regression"]["dispositions"]}
    raise ValueError("Repository case outside frozen extension")


def prepare_arm(run_id, arm_id, case_id):
    lock = design.freeze()
    blocks = [row for row in lock["blocks"] if row["block_id"] == run_id]
    if (len(blocks) != 1 or blocks[0]["repository_case_id"] != case_id or
            arm_id not in lock["arm_ids"]):
        raise ValueError("Repair case outside frozen arm")
    target = design.REPAIR_RUNTIME / run_id / arm_id
    if target.exists():
        raise FileExistsError("Repair arm already exists")
    target.mkdir(parents=True)
    inputs = material(case_id)
    if design.sha(inputs["prompt"]) != lock["dependencies_sha256"][
            "black_prompt" if case_id == "black_3" else "pysnooper_prompt"]:
        raise ValueError("Frozen repair prompt changed")
    with (target / "prompt.txt").open("xb") as stream:
        stream.write(inputs["prompt"].read_bytes())
    return target


def execute_once(*, run_id, arm_id, case_id, model_slot):
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman" or not os.environ.get(
            "MFEC_LITELLM_API_KEY"):
        raise ValueError("Rootful Podman and process-only provider credential required")
    lock = design.freeze()
    blocks = [row for row in lock["blocks"] if row["block_id"] == run_id]
    if (len(blocks) != 1 or blocks[0]["repository_case_id"] != case_id or
            arm_id not in lock["arm_ids"] or model_slot not in lock["models"]):
        raise ValueError("Repair request outside frozen scope")
    arm = design.REPAIR_RUNTIME / run_id / arm_id
    inputs = material(case_id)
    if design.sha(arm / "prompt.txt") != design.sha(inputs["prompt"]):
        raise ValueError("Repair prompt copy changed")
    provider = design.read(design.PROVIDER)
    matching = [row for row in provider["models"] if row["slot"] == model_slot]
    if (len(matching) != 1 or {key: matching[0][key] for key in (
            "model_id", "exact_version")} != lock["models"][model_slot]):
        raise ValueError("Provider mapping drift")
    job = arm / (case_id + "_" + model_slot)
    if job.exists():
        raise FileExistsError("Started repair attempt retained")
    job.mkdir()
    prompt = (arm / "prompt.txt").read_text(encoding="utf-8")
    design.save_new(job / "request_started.json", {
        "run_id": run_id, "arm_id": arm_id, "case_id": case_id,
        "model_slot": model_slot, "model_id": matching[0]["model_id"],
        "lock_sha256": design.sha(design.LOCK),
        "prompt_sha256": design.sha(arm / "prompt.txt"),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "automatic_retry": False})
    try:
        response = invoke(model={**matching[0], "base_url": provider["base_url"]},
                          case={"prompt": prompt}, generation=lock["generation"])
    except Exception as error:
        design.save_new(job / "provider_error.json", {
            "error_type": type(error).__name__,
            "http_status": getattr(error, "code", None),
            "billable_outcome_unknown": True})
        result = {"status": "PROVIDER_UNRESOLVED", "case_id": case_id,
                  "run_id": run_id, "arm_id": arm_id, "model_slot": model_slot}
        design.save_new(job / "summary.json", result)
        return result
    content = str(response.pop("content"))
    (job / "response.txt").write_text(content, encoding="utf-8")
    design.save_new(job / "provider.json", response)
    result = {"case_id": case_id, "run_id": run_id, "arm_id": arm_id,
              "model_slot": model_slot, "model_id": matching[0]["model_id"],
              "provider_request_id": response["provider_request_id"],
              "input_tokens": response["input_tokens"],
              "output_tokens": response["output_tokens"],
              "response_cost": response.get("response_cost"),
              "response_sha256": design.sha(job / "response.txt"),
              "returned_model_version": response["exact_model_version"]}
    if response["exact_model_version"] != matching[0]["exact_version"]:
        result["status"] = "PROVIDER_MAPPING_UNRESOLVED"
    elif response["finish_reason"] != "stop" or not content:
        result["status"] = "UNFINISHED_OR_EMPTY_OUTPUT"
    else:
        try:
            patch = to_patch(json.loads(content),
                             {inputs["source_path"]: inputs["source"]},
                             [inputs["source_path"]])
        except (ValueError, TypeError, KeyError) as error:
            result.update(status="EXACT_EDITS_CONTRACT_FAILED",
                          error_type=type(error).__name__)
        else:
            (job / "patch.diff").write_bytes(patch)
            result["patch_sha256"] = design.sha(job / "patch.diff")
            result["status"] = "VERIFIED"
            for label, nodes, expected in (
                ("visible", [inputs["visible"]], inputs["expected_visible"]),
                ("regression", inputs["regression_nodes"], inputs["expected_regression"]),
                ("replay_visible", [inputs["visible"]], inputs["expected_visible"]),
                ("replay_regression", inputs["regression_nodes"], inputs["expected_regression"]),
            ):
                check = execute_patch(job / "patch.diff", {"allowed_files": [
                    inputs["source_path"]]}, inputs["baseline"], label, nodes,
                    lock["repository_test_timeout_seconds"])
                result[label] = {"return_code": check["execution"]["return_code"],
                                 "timeout": bool(check["execution"].get("timeout")),
                                 "dispositions": check["dispositions"],
                                 "xml_sha256": check["xml_sha256"]}
                if result[label]["timeout"] or result[label]["return_code"] in (125, 126, 127):
                    result["status"] = "VERIFIER_ENVIRONMENT_UNRESOLVED"
                    break
                if result[label]["return_code"] != 0 or result[label]["dispositions"] != expected:
                    result["status"] = ("VISIBLE_TEST_FAILED" if label == "visible"
                                        else "PUBLIC_REGRESSION_OR_REPLAY_FAILED")
                    break
    design.save_new(job / "summary.json", result)
    return result
