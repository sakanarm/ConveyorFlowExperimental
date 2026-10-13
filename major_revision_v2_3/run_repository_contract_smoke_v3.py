"""Three-call exact-edits sentinel, frozen separately from prior repair pilots."""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
from audit_repository_repair_pilot_v1 import audit
from repository_exact_edits_v3 import to_patch
from run_repository_repair_pilot_v1 import invoke, execute_patch, sha, save, dispositions

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config_repository_contract_smoke_v3.json"
LOCK = HERE / "repository_contract_smoke_v3_lock.json"
OUT = HERE / "candidate_workspaces/repository_contract_smoke_v3"
PROVIDER = HERE.parent / "real_llm_pilot/config.mfec_main_frozen.json"


def freeze():
    if not audit()["audit_complete"]:
        raise ValueError("original pilot audit incomplete")
    inputs = {"config": sha(CONFIG), "runner": sha(Path(__file__)),
              "exact_edits": sha(HERE / "repository_exact_edits_v3.py"),
              "source_lock": sha(HERE / "repository_repair_pilot_v1_lock.json"),
              "source_auditor": sha(HERE / "audit_repository_repair_pilot_v1.py"),
              "bridge": sha(HERE / "wsl_contract_provider_bridge_v3.py")}
    settings = json.loads(CONFIG.read_text(encoding="utf-8"))
    contexts = {slot: sha(HERE / "candidate_workspaces/repository_repair_pilot_v1" /
                         (settings["case_id"] + "_" + slot) / "context.json") for slot in settings["model_slots"]}
    if LOCK.exists():
        frozen = json.loads(LOCK.read_text(encoding="utf-8"))
        if frozen["inputs"] != inputs or frozen["context_hashes"] != contexts:
            raise ValueError("sentinel inputs changed after freeze")
        return frozen
    frozen = {"status": "contract_sentinel_frozen_before_calls", "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "inputs": inputs, "settings": settings, "context_hashes": contexts, "research_results": False}
    save(LOCK, frozen)
    return frozen


def run(slot):
    frozen = freeze()
    settings = frozen["settings"]
    if slot not in settings["model_slots"]:
        raise ValueError("slot outside three-call sentinel")
    original = json.loads((HERE / "repository_repair_pilot_v1_lock.json").read_text(encoding="utf-8"))
    case = next(c for c in original["cases"] if c["case_id"] == settings["case_id"])
    baseline = next(c for c in original["baseline_audit"]["cases"] if c["case_id"] == case["case_id"])
    OUT.mkdir(exist_ok=True)
    job = OUT / (case["case_id"] + "_" + slot)
    job.mkdir()
    context = json.loads((HERE / "candidate_workspaces/repository_repair_pilot_v1" / job.name / "context.json").read_text(encoding="utf-8"))
    prompt = ('Repair the supplied buggy Python source. Emit the minimal repair immediately as JSON only. '
              'Do not emit analysis, markdown or a diff. Schema: {"edits":[{"path":"allowed/path.py",'
              '"before":"exact unique substring copied from buggy source","after":"replacement substring"}]}. '
              'Use one to eight nonoverlapping edits; before must match exactly once, including whitespace. '
              'Modify only allowed production files. No test/report manipulation, tools or network. Python 3.8.20. '
              'Return only edits, not full source files. No prose outside JSON.\n' + json.dumps(context, ensure_ascii=False))
    (job / "prompt.txt").write_text(prompt, encoding="utf-8")
    request = {"slot": slot, "case_id": case["case_id"], "prompt_sha256": sha(job / "prompt.txt"),
               "lock_sha256": sha(LOCK), "started_at_utc": datetime.now(timezone.utc).isoformat()}
    save(job / "request_started.json", request)
    provider = json.loads(PROVIDER.read_text(encoding="utf-8"))
    model = next(m for m in provider["models"] if m["slot"] == slot)
    print(json.dumps({**request, "status": "provider_request_started"}), flush=True)
    try:
        response = invoke(model={**model, "base_url": provider["base_url"]},
                          case={"prompt": prompt}, generation=settings["generation"])
    except Exception as error:
        save(job / "provider_error.json", {"type": type(error).__name__, "billable_outcome_unknown": True})
        row = {**request, "status": "PROVIDER_UNRESOLVED"}
    else:
        content = str(response.pop("content"))
        (job / "response.txt").write_text(content, encoding="utf-8")
        save(job / "provider.json", response)
        row = {**request, "provider_sha256": sha(job / "provider.json"), "response_sha256": sha(job / "response.txt")}
        if response["exact_model_version"] != model["exact_version"]:
            row["status"] = "PROVIDER_MAPPING_UNRESOLVED"
        elif response["finish_reason"] != "stop" or not content:
            row["status"] = "UNFINISHED_OR_EMPTY_OUTPUT"
        else:
            try:
                patch = to_patch(json.loads(content), context["allowed_source_files"], case["allowed_files"])
            except (ValueError, KeyError, TypeError) as error:
                row.update(status="EXACT_EDITS_CONTRACT_FAILED", error=str(error))
            else:
                path = job / "patch.diff";path.write_bytes(patch)
                row["patch_sha256"] = sha(path)
                builds = HERE / "results/bugsinpy_candidate_v1" / case["case_id"]
                expected = {n: "passed" for n in dispositions(builds / "candidate_buggy_visible_files/tests.xml")}
                regression = json.loads((builds / "regression_selection.json").read_text(encoding="utf-8"))["nodeids"]
                visible = execute_patch(path, case, baseline, "visible", [case["visible_test"]], settings["execution_timeout_seconds"])
                if visible["execution"].get("timeout"):
                    row["status"] = "EXECUTION_UNRESOLVED"
                elif visible["execution"]["return_code"] != 0 or visible["dispositions"] != expected:
                    row["status"] = "VISIBLE_TEST_FAILED"
                else:
                    checked = execute_patch(path, case, baseline, "regression", regression, settings["execution_timeout_seconds"])
                    if checked["execution"].get("timeout"):
                        row["status"] = "REGRESSION_UNRESOLVED"
                    elif checked["execution"]["return_code"] != 0 or checked["dispositions"] != baseline["dispositions"]:
                        row["status"] = "WITHHELD_PUBLIC_REGRESSION_FAILED"
                    else:
                        v = execute_patch(path, case, baseline, "replay_visible", [case["visible_test"]], settings["execution_timeout_seconds"])
                        r = execute_patch(path, case, baseline, "replay_regression", regression, settings["execution_timeout_seconds"])
                        ok = (v["execution"]["return_code"] == r["execution"]["return_code"] == 0 and
                              v["dispositions"] == expected and r["dispositions"] == baseline["dispositions"])
                        row["status"] = "VERIFIED" if ok else "CLEAN_REPLAY_UNRESOLVED"
    row.update(provider_calls=1, research_results=False, reused_case_not_independent=True,
               not_probability_calibration=True, not_allocation_comparison=True,
               completed_at_utc=datetime.now(timezone.utc).isoformat())
    save(job / "summary.json", row)
    print(json.dumps(row), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--model-slot")
    args = parser.parse_args()
    if args.freeze:
        print(json.dumps({"status": freeze()["status"], "max_provider_calls": 3}))
    elif args.model_slot:
        run(args.model_slot)
    else:
        parser.error("freeze or provide model slot")
