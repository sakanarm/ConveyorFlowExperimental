"""Read-only new-case first-attempt status, evidence audit and descriptive rates."""
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from audit_repository_baselines_v2 import dispositions
from repository_exact_edits_v3 import to_patch
from summarize_ecological_calibration import wilson
from run_repository_first_attempt_v1 import HERE, ROOT, LOCK, PREP, BUILDS, PROVIDER

OUTCOMES = {"VERIFIED", "PROVIDER_UNRESOLVED", "PROVIDER_MAPPING_UNRESOLVED",
            "UNFINISHED_OR_EMPTY_OUTPUT", "EXACT_EDITS_CONTRACT_FAILED", "EXECUTION_UNRESOLVED",
            "VISIBLE_TEST_FAILED", "WITHHELD_PUBLIC_REGRESSION_FAILED", "CLEAN_REPLAY_UNRESOLVED"}
UNCERTAIN = {"PROVIDER_UNRESOLVED", "PROVIDER_MAPPING_UNRESOLVED", "EXECUTION_UNRESOLVED", "CLEAN_REPLAY_UNRESOLVED"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit():
    frozen = json.loads(LOCK.read_text(encoding="utf-8"))
    special = {"provider_config": PROVIDER, "provider_adapter": PROVIDER.parent / "mfec_adapter.py",
               "preparation_lock": PREP / "lock.json", "preparation_summary": PREP / "summary.json",
               "build_lock": BUILDS / "lock.json", "build_summary": BUILDS / "summary.json"}
    for name, expected in frozen["dependencies"].items():
        if sha(special.get(name, HERE / name)) != expected:
            raise ValueError("frozen first-attempt dependency changed: " + name)
    cases = {c["case_id"]: c for c in frozen["cases"]}
    models = {m["slot"]: m for m in frozen["models"]}
    prepared = json.loads((PREP / "summary.json").read_text(encoding="utf-8"))
    rows, missing, in_progress, evidence, ids = [], [], [], [], set()
    for slot in frozen["settings"]["model_slots"]:
        ledger = ROOT / ("ledger_" + slot + ".jsonl")
        ledger_rows = [json.loads(s) for s in ledger.read_text(encoding="utf-8").splitlines() if s.strip()] if ledger.exists() else []
        if len({r["case_id"] for r in ledger_rows}) != len(ledger_rows) or any(r["slot"] != slot or r["case_id"] not in cases for r in ledger_rows):
            raise ValueError("duplicate/unknown ledger pair")
        completed_ids = []
        for cid, case in cases.items():
            prompt = ROOT / "frozen_prompts" / (cid + ".txt")
            if sha(prompt) != case["prompt_sha256"]:
                raise ValueError("frozen prompt changed")
            ready = next(r for r in prepared["cases"] if r["case_id"] == cid)
            if (not ready["source_mutation_import_confirmed"] or not ready["trusted_mutation_not_a_repair"]
                    or sha(PREP / cid / "identity_mutation.diff") != ready["mutation_patch_sha256"]
                    or sha(PREP / cid / "identity_mutation_visible/execution.json") != ready["mutation_execution_sha256"]):
                raise ValueError("trusted source-identity mutation evidence changed")
            if (sha(PREP / cid / "prompt_context.json") != ready["prompt_context_sha256"]
                    or sha(PREP / cid / "full_buggy_context.json") != ready["full_context_sha256"]
                    or sha(PREP / cid / "summary.json") != case["preparation_summary_sha256"]
                    or sha(BUILDS / cid / "regression_selection.json") != case["regression_selection_sha256"]):
                raise ValueError("prepared context/test evidence changed")
            job = ROOT / (cid + "_" + slot)
            if not (job / "request_started.json").exists():
                missing.append({"case_id": cid, "slot": slot})
                continue
            request = json.loads((job / "request_started.json").read_text(encoding="utf-8"))
            if (request["case_id"] != cid or request["slot"] != slot or request["lock_sha256"] != sha(LOCK)
                    or request["prompt_sha256"] != case["prompt_sha256"] or sha(job / "prompt.txt") != case["prompt_sha256"]
                    or request["started_at_utc"] <= frozen["created_at_utc"] or request["provider_calls"] != 1):
                raise ValueError("request lock/chronology/call count mismatch")
            if not (job / "summary.json").exists():
                in_progress.append({"case_id": cid, "slot": slot})
                continue
            row = json.loads((job / "summary.json").read_text(encoding="utf-8"))
            if (row not in ledger_rows or row["status"] not in OUTCOMES or row["provider_calls"] != 1
                    or any(row[k] != v for k, v in request.items()) or row["completed_at_utc"] < request["started_at_utc"]):
                raise ValueError("summary and append-only ledger disagree")
            if not all(row[k] is True for k in ("not_allocation_comparison", "not_difficulty_rank_calibration", "not_simulator_parameter_fit", "withheld_public_tests_not_novel_hidden_tests")):
                raise ValueError("scope flags missing")
            if row["status"] == "PROVIDER_UNRESOLVED":
                error = json.loads((job / "provider_error.json").read_text(encoding="utf-8"))
                if not error["billable_outcome_unknown"] or error["automatic_retry"]:
                    raise ValueError("provider uncertainty/retry evidence invalid")
            else:
                if sha(job / "provider.json") != row["provider_sha256"] or sha(job / "response.txt") != row["response_sha256"]:
                    raise ValueError("recorded response changed")
                provider = json.loads((job / "provider.json").read_text(encoding="utf-8"))
                rid = provider["provider_request_id"]
                if not rid or rid in ids:
                    raise ValueError("missing/duplicate provider request ID")
                ids.add(rid)
                if row["status"] != "PROVIDER_MAPPING_UNRESOLVED" and provider["exact_model_version"] != models[slot]["exact_version"]:
                    raise ValueError("model mapping changed without disposition")
                if provider["output_tokens"] > frozen["settings"]["generation"]["max_output_tokens"]:
                    raise ValueError("recorded output exceeds cap")
                if row["status"] in {"VISIBLE_TEST_FAILED", "WITHHELD_PUBLIC_REGRESSION_FAILED", "VERIFIED", "EXECUTION_UNRESOLVED", "CLEAN_REPLAY_UNRESOLVED"}:
                    full = json.loads((PREP / cid / "full_buggy_context.json").read_text(encoding="utf-8"))
                    patch = to_patch(json.loads((job / "response.txt").read_text(encoding="utf-8")), full["allowed_source_files"], case["allowed_files"])
                    if patch != (job / "patch.diff").read_bytes() or sha(job / "patch.diff") != row["patch_sha256"]:
                        raise ValueError("canonical patch does not match unmodified model edits")
                if row["status"] == "VERIFIED":
                    baseline = json.loads((BUILDS / cid / "summary.json").read_text(encoding="utf-8"))
                    expected = {n: "passed" for n in dispositions(BUILDS / cid / "candidate_buggy_visible_files/tests.xml")}
                    for label in ("visible", "regression", "replay_visible", "replay_regression"):
                        execution = json.loads((job / label / "execution.json").read_text(encoding="utf-8"))
                        wanted = expected if "visible" in label else baseline["reports"]["candidate_buggy_regression"]["dispositions"]
                        if execution["return_code"] != 0 or execution.get("timeout") or dispositions(job / label / "reports/tests.xml") != wanted:
                            raise ValueError("verified row lacks all four actual XML gates")
            completed_ids.append(cid)
            rows.append(row)
            evidence.append({"case_id": cid, "slot": slot, "file_hashes": {p.relative_to(job).as_posix(): sha(p) for p in job.rglob("*") if p.is_file()}})
        if [r["case_id"] for r in ledger_rows] != completed_ids:
            raise ValueError("slot ledger completion order differs from frozen case order")
    cells = []
    for slot in frozen["settings"]["model_slots"]:
        observed = [r for r in rows if r["slot"] == slot]
        counts = Counter(r["status"] for r in observed)
        verified = counts["VERIFIED"]
        unresolved = sum(counts[s] for s in UNCERTAIN)
        complete = len(observed) == len(cases)
        low, high = wilson(verified, len(cases)) if complete else (None, None)
        cells.append({"slot": slot, "model_alias": models[slot]["model_id"], "planned_pairs": len(cases), "completed_pairs": len(observed),
                      "verified": verified, "outcomes": dict(counts), "unresolved": unresolved,
                      "operational_verified_rate": verified / len(cases) if complete else None,
                      "wilson95_descriptive": [low, high], "possible_verified_rate_bounds_due_to_unresolved": [verified / len(cases), (verified + unresolved) / len(cases)] if complete else None,
                      "repository_clusters": sorted({c["project"] for c in cases.values()}), "not_an_independence_adjusted_population_interval": True})
    return {"status": "new_case_first_attempt_provenance_passed", "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "lock_sha256": sha(LOCK), "complete": len(rows) == len(cases) * len(models), "completed_pairs": len(rows),
            "planned_pairs": len(cases) * len(models), "missing": missing, "in_progress": in_progress, "cells": cells,
            "not_allocation_comparison": True, "not_difficulty_rank_calibration": True, "not_simulator_parameter_fit": True,
            "no_new_provider_calls_by_auditor": True, "records": evidence}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = audit()
    if args.out:
        with args.out.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))
