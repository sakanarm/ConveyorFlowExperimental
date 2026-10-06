"""Finalize audited stage feasibility, never call providers or run candidates.

Refuse partial results and existing output directories. Original frozen runners,
locks and append-only ledgers are never modified.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time

BASE = Path(__file__).resolve().parent
STAGES = ("ingest", "preprocess", "train", "package")
SLOTS = ("agent_1", "agent_2", "agent_3")


def summarize_complete_audit(audited, providers):
    if (not audited.get("complete") or audited.get("completed_pairs") != 36
            or audited.get("planned_pairs") != 36
            or audited.get("missing") or audited.get("in_progress")):
        raise ValueError("All 36 planned pairs must be completed before finalization")
    for name in ("not_probability_fit", "not_allocation_comparison", "not_held_out_calibration"):
        if audited.get(name) is not True:
            raise ValueError("Required feasibility scope qualification missing")
    cells = audited["cells"]
    expected = {(slot, stage) for slot in SLOTS for stage in STAGES}
    if (len(cells) != 12 or {(c["slot"], c["stage"]) for c in cells} != expected):
        raise ValueError("Missing or duplicate model-stage cell")
    overall = Counter()
    models = []
    for slot in SLOTS:
        selected = [c for c in cells if c["slot"] == slot]
        aliases = {c["model_alias"] for c in selected}
        if len(aliases) != 1:
            raise ValueError("Inconsistent deployment alias within slot")
        counts = Counter()
        stage_results = []
        for stage in STAGES:
            cell = next(c for c in selected if c["stage"] == stage)
            outcomes = cell["outcomes"]
            if (cell["planned_pairs"] != 3 or cell["completed_pairs"] != 3
                    or any(type(n) is not int or n < 0 for n in outcomes.values())
                    or sum(outcomes.values()) != 3
                    or cell["verified"] != outcomes.get("VERIFIED", 0)):
                raise ValueError("Cell denominator or verification accounting mismatch")
            counts.update(outcomes)
            stage_results.append({"stage": stage, "verified": cell["verified"], "planned_pairs": 3,
                                  "outcomes": outcomes})
        overall.update(counts)
        models.append({"slot": slot, "model_alias": next(iter(aliases)), "planned_pairs": 12,
                       "verified": counts["VERIFIED"], "outcomes": dict(counts), "stages": stage_results})
    provider_unresolved = overall["PROVIDER_UNRESOLVED"]
    if len(providers) != 36 - provider_unresolved:
        raise ValueError("Returned-response count differs from outcome accounting")
    ids = [p["provider_request_id"] for p in providers]
    if any(not request_id for request_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("Duplicate or missing returned provider request ID")
    for p in providers:
        if any(type(p[k]) is not int or p[k] < 0 for k in ("input_tokens", "output_tokens")):
            raise ValueError("Invalid token accounting")
        cost = p.get("response_cost")
        if cost is not None and (type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0):
            raise ValueError("Invalid recorded provider cost")
    costs = [p["response_cost"] for p in providers if p.get("response_cost") is not None]
    return {"planned_pairs": 36, "completed_pairs": 36, "verified": overall["VERIFIED"],
            "outcomes": dict(overall), "models": models,
            "returned_provider_responses": len(providers),
            "input_tokens_observed": sum(p["input_tokens"] for p in providers),
            "output_tokens_observed": sum(p["output_tokens"] for p in providers),
            "provider_reported_cost_observed_units": math.fsum(costs),
            "returned_responses_without_recorded_cost": len(providers) - len(costs),
            "provider_calls_with_unknown_billable_outcome": provider_unresolved,
            "cost_currency_confirmed": False, "not_total_billed_cost": True,
            "not_probability_fit": True, "not_allocation_comparison": True,
            "not_held_out_calibration": True, "source_corpora": 2,
            "trusted_predecessors_not_candidate_full_pipeline": True}


def render_report(summary, audit_hash):
    lines = ["# ML isolated-stage v2: completed feasibility results", "",
             "This is supporting execution evidence, not a policy comparison or held-out probability calibration.", "",
             "## Why this experiment was run", "",
             "A sequential DAG censors later stages when an earlier stage fails. Here every model receives the same frozen inputs and trusted predecessor artifacts for every stage. This tests bounded stage execution and interoperability without treating uncalled stages as model failures. It does not test a complete pipeline built by that model.", "",
             "The three reused specifications are Adult P1, Adult P2, and Beijing P1, from only two source corpora. Earlier exposure was disclosed before these calls. The unexecuted V1 capsule is preserved; V2 is a separately frozen reused-specification diagnostic.", "",
             "Each of 36 planned model–specification–stage pairs has one provider call, temperature 0, an output cap of 32,768, and the same bounded verifier. Successful unchanged source is checked again in a fresh replay. No candidate source is repaired by the investigator. Replays are not extra observations.", "",
             "## Completed first-attempt accounting", "",
             "| Model alias | Ingest /3 | Preprocess /3 | Train /3 | Package /3 | Verified /12 |",
             "|---|---:|---:|---:|---:|---:|"]
    for model in summary["models"]:
        stages = {c["stage"]: c["verified"] for c in model["stages"]}
        lines.append("| " + model["model_alias"] + " | " + " | ".join(str(stages[s]) for s in STAGES)
                     + " | " + str(model["verified"]) + " |")
    lines += ["", "Outcome counts: " + json.dumps(summary["outcomes"], sort_keys=True) + ".", "",
              "PROVIDER_UNRESOLVED is not an observed patch/code failure. It remains in planned operational accounting and is reported separately. Output-format, artifact-contract, execution, and replay failures are retained; nothing is rerun merely to obtain a passing outcome.", "",
              "## Recorded resources", "",
              f"Returned responses: {summary['returned_provider_responses']}; observed input tokens: {summary['input_tokens_observed']:,}; observed output tokens: {summary['output_tokens_observed']:,}; observed provider-reported cost: {summary['provider_reported_cost_observed_units']:.9f} units.", "",
              f"Unknown billable outcomes: {summary['provider_calls_with_unknown_billable_outcome']}; returned responses without recorded cost: {summary['returned_responses_without_recorded_cost']}. Currency is unconfirmed. These observations are not a total billed cost. Shared sandbox serialization and its queue time are controlled harness overhead, not evidence of concurrent allocation throughput.", "",
              "## Interpretation within the advisor's research framework", "",
              "The paper's scientific contribution remains decentralized self-selection, capability heterogeneity, and capability–task fit/stand-down on the READY belt. Stage execution is an instrument used to check that real work can be executed and verified. It is not an additional AutoML contribution.", "",
              "These small, correlated, reused probes cannot establish universal Ability Ranks or a difficulty-response curve. They cannot be pooled with full-DAG jobs, repository attempts, microtasks, or simulation runs. They also cannot establish that CF-Fit outperforms Central-Fit, Central-Matched, or static allocation. RQ1 remains a trade-off question; RQ2 and ablations require their own team and mechanism contrasts.", "",
              "Held-out ecological calibration, locked profiles and paired live allocation streams remain separate gates before claiming the major-revision evidence is complete.", "",
              "## Provenance", "", f"Final audit SHA256: `{audit_hash}`.", "",
              "The audit verifies frozen dependencies, exposure inventory, request chronology, prompt/source hashes, common inputs/predecessors, ledger order, and successful initial/fresh-replay gates. See audit.json and summary.json in this capsule. No provider calls or candidate execution are performed by this finalizer.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--wait-seconds", type=int, default=0,
                        help="Optionally wait up to 1800 seconds for already-started workers; no launches or retries")
    args = parser.parse_args()
    if not 0 <= args.wait_seconds <= 1800:
        parser.error("--wait-seconds must be between 0 and 1800")
    destination = args.out_dir.resolve()
    if not destination.is_relative_to(BASE / "results"):
        raise ValueError("Final capsule must stay inside this experiment's results directory")
    if destination.exists():
        raise FileExistsError("Refusing to overwrite an existing final capsule")
    from audit_ml_isolated_stage_pilot_v2 import audit
    from run_ml_isolated_stage_pilot_v2 import ROOT, LOCK
    if args.wait_seconds:
        frozen = json.loads(LOCK.read_text(encoding="utf-8"))
        summaries = [ROOT / (probe["probe_id"] + "_" + slot) / "summary.json"
                     for slot in frozen["model_slots"] for probe in frozen["probes"]]
        # File presence is only a waiting signal. The full provenance audit below
        # must still pass before any final output is written.
        deadline = time.monotonic() + args.wait_seconds
        while not all(path.is_file() for path in summaries):
            left = deadline - time.monotonic()
            if left <= 0:
                parser.exit(2, json.dumps({"status": "not_finalized_wait_expired",
                                          "output_created": False, "no_provider_calls": True}) + "\n")
            print(json.dumps({"status": "waiting_for_existing_workers",
                              "summary_files_present_not_yet_final_audited": sum(path.is_file() for path in summaries),
                              "planned_pairs": len(summaries), "no_provider_calls": True}), flush=True)
            time.sleep(min(30, left))
    audited = audit()
    if not audited.get("complete"):
        parser.exit(2, json.dumps({"status": "not_finalized_incomplete_batch",
                                  "completed_pairs": audited["completed_pairs"],
                                  "planned_pairs": audited["planned_pairs"],
                                  "output_created": False, "no_provider_calls": True}) + "\n")
    providers = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(ROOT.glob("*/provider.json"))]
    summary = summarize_complete_audit(audited, providers)
    summary["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    summary["lock_sha256"] = audited["lock_sha256"]
    audit_bytes = (json.dumps(audited, indent=2) + "\n").encode("utf-8")
    audit_hash = hashlib.sha256(audit_bytes).hexdigest()
    summary["audit_sha256"] = audit_hash
    report = render_report(summary, audit_hash)
    destination.mkdir()
    (destination / "audit.json").write_bytes(audit_bytes)
    (destination / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (destination / "RESULTS.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": "completed_stage_feasibility_finalized", "output": str(destination),
                      "completed_pairs": 36, "verified": summary["verified"],
                      "audit_sha256": audit_hash, "no_provider_calls": True}))


if __name__ == "__main__":
    main()
