"""Read-only sentinel audit; never calls a provider or executes candidate code."""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from audit_repository_repair_pilot_v1 import audit, sha
from audit_repository_baselines_v2 import dispositions
from repository_exact_edits_v3 import to_patch

HERE = Path(__file__).resolve().parent
LOCK = HERE / "repository_contract_smoke_v3_lock.json"
ROOT = HERE / "candidate_workspaces/repository_contract_smoke_v3"


def check():
    if not audit()["audit_complete"]:
        raise ValueError("original pilot audit incomplete")
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    dependencies = {
        "config": "config_repository_contract_smoke_v3.json",
        "runner": "run_repository_contract_smoke_v3.py",
        "exact_edits": "repository_exact_edits_v3.py",
        "source_lock": "repository_repair_pilot_v1_lock.json",
        "source_auditor": "audit_repository_repair_pilot_v1.py",
        "bridge": "wsl_contract_provider_bridge_v3.py",
    }
    for key, name in dependencies.items():
        if sha(HERE / name) != lock["inputs"][key]:
            raise ValueError("sentinel frozen dependency changed: " + key)
    settings = json.loads((HERE / dependencies["config"]).read_text(encoding="utf-8"))
    if settings != lock["settings"] or settings["max_provider_calls"] != 3:
        raise ValueError("sentinel settings or request budget changed")
    source = json.loads((HERE / dependencies["source_lock"]).read_text(encoding="utf-8"))
    case = next(c for c in source["cases"] if c["case_id"] == settings["case_id"])
    baseline = next(c for c in source["baseline_audit"]["cases"] if c["case_id"] == settings["case_id"])
    models = json.loads((HERE.parent / "real_llm_pilot/config.mfec_main_frozen.json").read_text(encoding="utf-8"))["models"]
    expected_jobs = {settings["case_id"] + "_" + slot for slot in settings["model_slots"]}
    if {p.name for p in ROOT.iterdir() if p.is_dir()} != expected_jobs:
        raise ValueError("missing or extra sentinel job directory")
    requests = set()
    prompts = set()
    records = []
    tokens = Counter()
    cost = 0.0
    cost_unknown = 0
    for slot in settings["model_slots"]:
        job = ROOT / (settings["case_id"] + "_" + slot)
        row = json.loads((job / "summary.json").read_text(encoding="utf-8"))
        request = json.loads((job / "request_started.json").read_text(encoding="utf-8"))
        context_path = HERE / "candidate_workspaces/repository_repair_pilot_v1" / job.name / "context.json"
        if sha(context_path) != lock["context_hashes"][slot]:
            raise ValueError("original buggy context changed")
        if any(row.get(k) != v for k, v in request.items()):
            raise ValueError("request/summary identity mismatch")
        if (request["slot"] != slot or request["case_id"] != settings["case_id"]
                or request["lock_sha256"] != sha(LOCK)
                or request["prompt_sha256"] != sha(job / "prompt.txt")
                or request["started_at_utc"] <= lock["created_at_utc"]
                or row["completed_at_utc"] < request["started_at_utc"]):
            raise ValueError("sentinel request identity, chronology or prompt changed")
        prompts.add(request["prompt_sha256"])
        if row["provider_calls"] != 1 or row["research_results"] is not False:
            raise ValueError("sentinel request accounting or claim changed")
        for flag in ("reused_case_not_independent", "not_probability_calibration", "not_allocation_comparison"):
            if row.get(flag) is not True:
                raise ValueError("sentinel limitations missing")
        provider = json.loads((job / "provider.json").read_text(encoding="utf-8"))
        if sha(job / "provider.json") != row["provider_sha256"] or sha(job / "response.txt") != row["response_sha256"]:
            raise ValueError("provider evidence changed")
        request_id = provider["provider_request_id"]
        if not request_id or request_id in requests:
            raise ValueError("missing or repeated provider request ID")
        requests.add(request_id)
        model = next(m for m in models if m["slot"] == slot)
        if provider["exact_model_version"] != model["exact_version"]:
            raise ValueError("provider deployment mapping changed")
        for field in ("input_tokens", "output_tokens"):
            value = provider[field]
            if not isinstance(value, int) or value < 0:
                raise ValueError("invalid provider token count")
            tokens[field] += value
        if provider["output_tokens"] > settings["generation"]["max_output_tokens"]:
            raise ValueError("provider output exceeds sentinel cap")
        value = provider.get("response_cost")
        if value is None:
            cost_unknown += 1
        elif not isinstance(value, (int, float)) or value < 0:
            raise ValueError("invalid provider-reported cost")
        else:
            cost += value
        content = (job / "response.txt").read_text(encoding="utf-8")
        if row["status"] == "UNFINISHED_OR_EMPTY_OUTPUT":
            if provider["finish_reason"] == "stop" and content:
                raise ValueError("completed content mislabeled as unavailable")
            if (job / "patch.diff").exists():
                raise ValueError("unfinished response must not be executed")
        elif row["status"] in {"VISIBLE_TEST_FAILED", "VERIFIED"}:
            if provider["finish_reason"] != "stop":
                raise ValueError("unfinished response used as a candidate patch")
            context = json.loads(context_path.read_text(encoding="utf-8"))
            canonical = to_patch(json.loads(content), context["allowed_source_files"], case["allowed_files"])
            if canonical != (job / "patch.diff").read_bytes() or sha(job / "patch.diff") != row["patch_sha256"]:
                raise ValueError("candidate edits or canonical patch changed")
            known = dispositions(HERE / "results/bugsinpy_candidate_v1" / case["case_id"] / "candidate_buggy_visible_files/tests.xml")
            expected_visible = {n: "passed" for n in known}
            labels = ("visible", "regression", "replay_visible", "replay_regression") if row["status"] == "VERIFIED" else ("visible",)
            for label in labels:
                directory = job / label
                execution = json.loads((directory / "execution.json").read_text(encoding="utf-8"))
                actual = dispositions(directory / "reports/tests.xml")
                expected = expected_visible if "visible" in label else baseline["dispositions"]
                passed = execution["return_code"] == 0 and not execution.get("timeout") and actual == expected
                if row["status"] == "VERIFIED" and not passed:
                    raise ValueError("verified sentinel lacks a complete passing test gate")
                if row["status"] == "VISIBLE_TEST_FAILED" and passed:
                    raise ValueError("passing visible tests mislabeled as failure")
        else:
            raise ValueError("unhandled sentinel disposition; audit must be explicitly extended")
        records.append({"model_slot": slot, "case_id": case["case_id"], "status": row["status"],
                        "provider_request_id": request_id, "input_tokens": provider["input_tokens"],
                        "output_tokens": provider["output_tokens"], "response_cost": value,
                        "artifact_hashes": {p.relative_to(job).as_posix(): sha(p) for p in job.rglob("*") if p.is_file()}})
    if len(prompts) != 1 or len(requests) != settings["max_provider_calls"]:
        raise ValueError("prompt equality or three-call sentinel coverage failed")
    return {"status": "contract_sentinel_audit_passed", "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "lock_sha256": sha(LOCK), "completed_jobs": len(records), "provider_calls": len(requests),
            "job_statuses": dict(Counter(r["status"] for r in records)), "tokens": dict(tokens),
            "provider_reported_cost_units": cost, "cost_unknown_responses": cost_unknown,
            "currency_not_confirmed": True, "research_results": False, "reused_case_not_independent": True,
            "not_probability_calibration": True, "not_allocation_comparison": True, "records": records}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = check()
    if args.out:
        with args.out.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))
