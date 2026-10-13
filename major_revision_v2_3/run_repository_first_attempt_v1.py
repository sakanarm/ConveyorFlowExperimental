"""New-case first-attempt localized repairs; three aliases, no automatic retry.

Descriptive observations only, not difficulty-specific ability ranks, simulator
parameter fitting, or an allocation comparison. Prior feasibility cases excluded.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from audit_repository_baselines_v2 import dispositions
from build_repository_calibration_candidates_final_v4 import OUT as BUILDS, freeze as build_freeze
from prepare_repository_first_attempt_v1 import OUT as PREP, freeze as preparation_freeze
from repository_exact_edits_v3 import to_patch
from run_repository_repair_pilot_v1 import invoke, execute_patch, save, sha

HERE = Path(__file__).resolve().parent
PROVIDER = HERE.parent / "real_llm_pilot/config.mfec_main_frozen.json"
ROOT = HERE / "candidate_workspaces/repository_first_attempt_v1"
LOCK = HERE / "repository_first_attempt_v1_lock.json"
SETTINGS = {
    "model_slots": ["agent_1", "agent_2", "agent_3"],
    "case_count": 6, "max_provider_calls": 18, "max_attempts_per_case_model": 1,
    "generation": {"temperature": 0, "max_output_tokens": 32768, "timeout_seconds": 720},
    "execution_timeout_seconds": 180,
    "estimand": "First-attempt verified localized-repair rate on these six new, environment-supported cases, under the frozen exact-edits/excerpts/test budget. Not a population-wide capability or difficulty-specific success curve.",
    "denominator": "Every planned case-model pair. Unfinished/schema/apply/test failure and unresolved provider/execution outcomes stay in the operational denominator. Missing rows stay missing, not failures. Also report unresolved counts and conservative bounds if provider completion is unknown.",
    "statistics": "Observed rates and descriptive Wilson 95% intervals per deployment, with repository clusters disclosed; n=6, no significance tests/rank promotion/D1-D3 fit. No pooling with older pilots or reused sentinels.",
    "retry_rule": "One provider invocation per pair, SDK retries disabled. Never rerun a pair whose request has started; retain partial evidence. Fresh container replay of the same patch is verification, not a model retry.",
    "execution_order": "Frozen case order within each alias; three alias workers may run concurrently. Request timestamps/window specificity are reported. This is not a randomized causal comparison of model vendors.",
}
INSTRUCTION = (
    'Repair the supplied buggy Python source. Emit the minimal repair immediately as JSON only. '
    'Do not emit analysis, markdown or a diff. Schema: {"edits":[{"path":"allowed/path.py",'
    '"before":"exact unique substring copied from buggy source","after":"replacement substring"}]}. '
    'Use one to eight nonoverlapping edits; before must match exactly once in the original full file, including whitespace. '
    'Modify only allowed production files. No test/report manipulation, tools or network. Python 3.8.20. '
    'Long files may be shown as verbatim source ranges with line numbers; do not include line numbers or omission markers in before/after. '
    'Return only edits, not full source files. No prose outside JSON.\n'
)


def now():
    return datetime.now(timezone.utc).isoformat()


def freeze():
    build = build_freeze()
    preparation_freeze()
    ready = json.loads((PREP / "summary.json").read_text(encoding="utf-8"))
    if ready["status"] != "first_attempt_preparation_ready" or len(ready["cases"]) != SETTINGS["case_count"]:
        raise ValueError("new-case identity checks/context freeze not complete")
    dependencies = {name: sha(HERE / name) for name in (
        "run_repository_first_attempt_v1.py", "prepare_repository_first_attempt_v1.py",
        "build_repository_calibration_candidates_v1.py", "repository_exact_edits_v3.py",
        "build_repository_calibration_candidates_recovery_v2.py",
        "build_repository_calibration_candidates_amendment_v3.py",
        "build_repository_calibration_candidates_final_v4.py",
        "repository_patch_guard_v1.py", "run_repository_repair_pilot_v1.py",
        "build_bugsinpy_candidate_v1.py", "audit_repository_baselines_v2.py",
        "run_bugsinpy_preflight.py", "container_cli.py", "wsl_repository_first_attempt_bridge_v1.py")}
    dependencies.update({"provider_config": sha(PROVIDER), "provider_adapter": sha(PROVIDER.parent / "mfec_adapter.py"),
                         "preparation_lock": sha(PREP / "lock.json"), "preparation_summary": sha(PREP / "summary.json"),
                         "build_lock": sha(BUILDS / "lock.json"), "build_summary": sha(BUILDS / "summary.json")})
    prompts = {}
    cases = []
    for case in build["cases"]:
        cid = case["case_id"]
        row = next(r for r in ready["cases"] if r["case_id"] == cid)
        if not row["source_mutation_import_confirmed"] or not row["trusted_mutation_not_a_repair"]:
            raise ValueError("submitted source import has not been demonstrated")
        for name, field in (("full_buggy_context.json", "full_context_sha256"), ("prompt_context.json", "prompt_context_sha256")):
            if sha(PREP / cid / name) != row[field]:
                raise ValueError("prepared buggy context changed")
        if sha(BUILDS / cid / "summary.json") != row["candidate_summary_sha256"]:
            raise ValueError("candidate baseline changed")
        context = json.loads((PREP / cid / "prompt_context.json").read_text(encoding="utf-8"))
        prompts[cid] = INSTRUCTION + json.dumps(context, ensure_ascii=False)
        cases.append({**case, "prompt_sha256": hashlib.sha256(prompts[cid].encode()).hexdigest(),
                      "preparation_summary_sha256": sha(PREP / cid / "summary.json"),
                      "regression_selection_sha256": sha(BUILDS / cid / "regression_selection.json")})
    provider = json.loads(PROVIDER.read_text(encoding="utf-8"))
    stable = {"dependencies": dependencies, "settings": SETTINGS, "cases": cases,
              "models": [{k: m[k] for k in ("slot", "model_id", "exact_version")} for m in provider["models"]]}
    if {m["slot"] for m in stable["models"]} != set(SETTINGS["model_slots"]):
        raise ValueError("deployment aliases differ from declared team")
    ROOT.mkdir(exist_ok=True)
    if LOCK.exists():
        frozen = json.loads(LOCK.read_text(encoding="utf-8"))
        if any(frozen[k] != v for k, v in stable.items()):
            raise ValueError("first-attempt protocol changed after freeze")
        return frozen, prompts
    frozen = {**stable, "created_at_utc": now(), "status": "new_case_first_attempt_frozen_before_calls",
              "not_allocation_comparison": True, "not_difficulty_rank_calibration": True, "not_simulator_parameter_fit": True}
    save(LOCK, frozen)
    for cid, prompt in prompts.items():
        folder = ROOT / "frozen_prompts"
        folder.mkdir(exist_ok=True)
        with (folder / (cid + ".txt")).open("x", encoding="utf-8") as handle:
            handle.write(prompt)
    return frozen, prompts


def run(cid, slot):
    frozen, prompts = freeze()
    if slot not in SETTINGS["model_slots"]:
        raise ValueError("unknown model slot")
    case = next(c for c in frozen["cases"] if c["case_id"] == cid)
    for earlier in frozen["cases"][:frozen["cases"].index(case)]:
        if not (ROOT / (earlier["case_id"] + "_" + slot) / "summary.json").exists():
            raise ValueError("first-attempt pairs must follow frozen case order within the alias")
    job = ROOT / (cid + "_" + slot)
    if job.exists():
        if (job / "summary.json").exists():
            return json.loads((job / "summary.json").read_text(encoding="utf-8"))
        raise FileExistsError("started/incomplete pair cannot be silently retried")
    job.mkdir()
    provider = json.loads(PROVIDER.read_text(encoding="utf-8"))
    model = next(m for m in provider["models"] if m["slot"] == slot)
    prompt = prompts[cid]
    (job / "prompt.txt").write_text(prompt, encoding="utf-8")
    if sha(job / "prompt.txt") != case["prompt_sha256"]:
        raise ValueError("call prompt does not match frozen bytes")
    row = {"case_id": cid, "project": case["project"], "slot": slot, "model_alias": model["model_id"],
           "prompt_sha256": case["prompt_sha256"], "lock_sha256": sha(LOCK), "started_at_utc": now(), "provider_calls": 1}
    save(job / "request_started.json", row)
    print(json.dumps({**row, "status": "provider_request_started"}), flush=True)
    try:
        response = invoke(model={**model, "base_url": provider["base_url"]}, case={"prompt": prompt}, generation=SETTINGS["generation"])
    except Exception as error:
        save(job / "provider_error.json", {"type": type(error).__name__, "billable_outcome_unknown": True, "automatic_retry": False})
        row["status"] = "PROVIDER_UNRESOLVED"
    else:
        content = str(response.pop("content"))
        (job / "response.txt").write_text(content, encoding="utf-8")
        save(job / "provider.json", response)
        row.update(provider_sha256=sha(job / "provider.json"), response_sha256=sha(job / "response.txt"))
        if response["exact_model_version"] != model["exact_version"]:
            row["status"] = "PROVIDER_MAPPING_UNRESOLVED"
        elif response["finish_reason"] != "stop" or not content:
            row["status"] = "UNFINISHED_OR_EMPTY_OUTPUT"
        else:
            context = json.loads((PREP / cid / "full_buggy_context.json").read_text(encoding="utf-8"))
            try:
                patch = to_patch(json.loads(content), context["allowed_source_files"], case["allowed_files"])
            except (ValueError, KeyError, TypeError, UnicodeError) as error:
                row.update(status="EXACT_EDITS_CONTRACT_FAILED", error=str(error))
            else:
                path = job / "patch.diff"
                path.write_bytes(patch)
                row["patch_sha256"] = sha(path)
                summary = json.loads((BUILDS / cid / "summary.json").read_text(encoding="utf-8"))
                baseline = {"images": summary["images"], "dispositions": summary["reports"]["candidate_buggy_regression"]["dispositions"]}
                expected = {n: "passed" for n in dispositions(BUILDS / cid / "candidate_buggy_visible_files/tests.xml")}
                targets = summary["regression_nodeids"]
                row["status"] = "VERIFIED"
                for label, nodes, known in (("visible", [case["visible_test"]], expected),
                                            ("regression", targets, baseline["dispositions"]),
                                            ("replay_visible", [case["visible_test"]], expected),
                                            ("replay_regression", targets, baseline["dispositions"])):
                    result = execute_patch(path, case, baseline, label, nodes, SETTINGS["execution_timeout_seconds"])
                    if result["execution"].get("timeout"):
                        row["status"] = "EXECUTION_UNRESOLVED"
                        break
                    if result["execution"]["return_code"] != 0 or result["dispositions"] != known:
                        row["status"] = {"visible": "VISIBLE_TEST_FAILED", "regression": "WITHHELD_PUBLIC_REGRESSION_FAILED"}.get(label, "CLEAN_REPLAY_UNRESOLVED")
                        break
    row.update(completed_at_utc=now(), not_allocation_comparison=True, not_difficulty_rank_calibration=True,
               not_simulator_parameter_fit=True, withheld_public_tests_not_novel_hidden_tests=True)
    save(job / "summary.json", row)
    with (ROOT / ("ledger_" + slot + ".jsonl")).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps(row), flush=True)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--slot")
    parser.add_argument("--case-id")
    args = parser.parse_args()
    if args.freeze:
        frozen, _ = freeze()
        print(json.dumps({"status": frozen["status"], "cases": len(frozen["cases"]), "max_provider_calls": SETTINGS["max_provider_calls"]}))
    elif args.slot:
        frozen, _ = freeze()
        cases = [args.case_id] if args.case_id else [c["case_id"] for c in frozen["cases"]]
        for cid in cases:
            run(cid, args.slot)
    else:
        parser.error("freeze or slot")


if __name__ == "__main__":
    main()
