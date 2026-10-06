"""Read-only isolated-stage progress, source/response hashes and gate audit."""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from run_ml_isolated_stage_pilot_v1 import LOCK, ROOT, PREP, dependencies, verify_preparation, sha256
from run_ml_dag_stage import PREDECESSOR, SCRIPT
from run_ml_dag_llm_feasibility import decode_stage_source

OUTCOMES = {"VERIFIED", "PROVIDER_UNRESOLVED", "PROVIDER_MAPPING_UNRESOLVED", "GENERATION_CONTRACT_FAILED",
            "STAGE_CONTRACT_FAILED", "ENVIRONMENT_UNRESOLVED", "REPLAY_UNRESOLVED", "REPLAY_CONTRACT_FAILED"}


def checked_gate(job, label, probe, source_hash):
    path = job / ("gates.json" if label == "attempt" else "replay_gates.json")
    gate = json.loads(path.read_text())
    bundle = job / label
    report = json.loads((bundle / "dag_output" / probe["stage"] / "stage_report.json").read_text())
    if gate["stage_report"] != report or report["source_sha256"] != source_hash:
        raise ValueError("gate/source evidence mismatch")
    if report["execution"]["return_code"] != 0 or report["execution"]["timed_out"] or not report["verified"]:
        raise ValueError("verified outcome has failed execution")
    if probe["stage"] in {"preprocess", "train"}:
        compatibility = json.loads((bundle / ("compatibility_first_attempt" if label == "attempt" else "compatibility_fresh_replay") / "report.json").read_text())
        if gate["compatibility"] != compatibility or not compatibility["verified"] or compatibility["execution"]["return_code"] != 0:
            raise ValueError("semantic/interoperability gate missing")
    if not gate["verified"] or gate["environment_unresolved"]:
        raise ValueError("incorrect verified gate")


def audit():
    frozen = json.loads(LOCK.read_text())
    if frozen["dependencies"] != dependencies():
        raise ValueError("isolated-stage frozen dependencies changed")
    verify_preparation()
    models = {m["slot"]: m for m in frozen["models"]}
    records, missing, pending, ids = [], [], [], set()
    evidence = []
    for slot in frozen["model_slots"]:
        path = ROOT / ("ledger_" + slot + ".jsonl")
        ledger = [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []
        completed = []
        for probe in frozen["probes"]:
            job = ROOT / (probe["probe_id"] + "_" + slot)
            if not (job / "request_started.json").exists():
                missing.append({"probe_id": probe["probe_id"], "slot": slot})
                continue
            started = json.loads((job / "request_started.json").read_text())
            if (any(started[k] != v for k, v in probe.items()) or started["slot"] != slot
                    or started["lock_sha256"] != sha256(LOCK) or started["provider_calls"] != 1
                    or started["started_at_utc"] <= frozen["created_at_utc"]
                    or sha256(job / "prompt.txt") != probe["prompt_sha256"]):
                raise ValueError("request chronology/identity/prompt/call-count mismatch")
            if not (job / "summary.json").exists():
                pending.append({"probe_id": probe["probe_id"], "slot": slot})
                continue
            result = json.loads((job / "summary.json").read_text())
            if (result not in ledger or result["status"] not in OUTCOMES
                    or any(result[k] != v for k, v in started.items())
                    or result["completed_at_utc"] < started["started_at_utc"]):
                raise ValueError("ledger/summary mismatch")
            if not all(result[k] for k in ("not_probability_fit", "not_allocation_comparison", "trusted_predecessors_not_candidate_pipeline")):
                raise ValueError("scope qualification missing")
            if result["status"] == "PROVIDER_UNRESOLVED":
                error = json.loads((job / "provider_error.json").read_text())
                if not error["billable_outcome_unknown"] or error["automatic_retry"]:
                    raise ValueError("unresolved billing incorrectly reported")
            else:
                provider = json.loads((job / "provider.json").read_text())
                if sha256(job / "provider.json") != result["provider_sha256"] or sha256(job / "response.txt") != result["response_sha256"]:
                    raise ValueError("response evidence changed")
                if provider["provider_request_id"] in ids or not provider["provider_request_id"]:
                    raise ValueError("duplicate/missing provider ID")
                ids.add(provider["provider_request_id"])
                if provider["output_tokens"] > frozen["generation"]["max_output_tokens"]:
                    raise ValueError("output cap exceeded")
                if result["status"] != "PROVIDER_MAPPING_UNRESOLVED" and provider["exact_model_version"] != models[slot]["exact_version"]:
                    raise ValueError("unrecorded deployment mapping drift")
                if result["status"] not in {"GENERATION_CONTRACT_FAILED", "PROVIDER_MAPPING_UNRESOLVED"}:
                    source = decode_stage_source(probe["stage"], (job / "response.txt").read_text(), provider["finish_reason"])
                    candidate = job / "attempt/submission" / SCRIPT[probe["stage"]]
                    if source != candidate.read_text() or sha256(candidate) != result["source_sha256"]:
                        raise ValueError("source is not the unchanged provider output")
                if result["status"] == "VERIFIED":
                    repeated = job / "replay/submission" / SCRIPT[probe["stage"]]
                    if sha256(repeated) != result["source_sha256"]:
                        raise ValueError("replay source changed")
                    checked_gate(job, "attempt", probe, result["source_sha256"])
                    checked_gate(job, "replay", probe, result["source_sha256"])
            for label in ("attempt",):
                source_bundle = PREP / probe["probe_id"]
                actual_bundle = job / label
                for p in (source_bundle / "input").glob("*.csv"):
                    if sha256(p) != sha256(actual_bundle / "input" / p.name):
                        raise ValueError("input differs from frozen common input")
                for previous in PREDECESSOR[probe["stage"]]:
                    for p in (source_bundle / "dag_output" / previous).rglob("*"):
                        if p.is_file() and sha256(p) != sha256(actual_bundle / "dag_output" / previous / p.relative_to(source_bundle / "dag_output" / previous)):
                            raise ValueError("trusted predecessor differs across deployments")
            completed.append(result)
            records.append(result)
            evidence.append({"probe_id": probe["probe_id"], "slot": slot, "file_sha256": {p.relative_to(job).as_posix(): sha256(p) for p in job.rglob("*") if p.is_file()}})
        if ledger != completed:
            raise ValueError("ledger duplicates or non-frozen order")
    cells = []
    for slot in frozen["model_slots"]:
        for stage in ("ingest", "preprocess", "train", "package"):
            observed = [r for r in records if r["slot"] == slot and r["stage"] == stage]
            counts = Counter(r["status"] for r in observed)
            cells.append({"slot": slot, "model_alias": models[slot]["model_id"], "stage": stage,
                          "planned_pairs": 3, "completed_pairs": len(observed), "verified": counts["VERIFIED"],
                          "outcomes": dict(counts), "not_independent_corpus_observations": True})
    return {"status": "isolated_stage_pilot_provenance_passed", "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "lock_sha256": sha256(LOCK), "complete": len(records) == 36, "planned_pairs": 36,
            "completed_pairs": len(records), "missing": missing, "in_progress": pending,
            "cells": cells, "not_probability_fit": True, "not_allocation_comparison": True,
            "source_corpora": 2, "no_provider_calls_by_auditor": True, "evidence": evidence}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = audit()
    if args.out:
        with args.out.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "evidence"}, indent=2))
