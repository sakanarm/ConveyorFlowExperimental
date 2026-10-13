"""Read-only audit of prepared inputs and trusted fixture checks; no live calls."""
from contextlib import closing
import csv
import json
from pathlib import Path
import sqlite3

from prepare_design import audit as audit_design, DEST, HERE, MAJOR, sha256
from run_dry import fixture_run


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def audit_public_csv(path, *, development, excluded):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if (len(set(fields)) != len(fields) or "row_id" not in fields
                or ("target" in fields) != development or set(excluded) & set(fields)):
            raise ValueError("Public CSV schema/target separation failed")
        ids = set()
        for row in reader:
            if None in row or None in row.values() or not row["row_id"] or row["row_id"] in ids:
                raise ValueError("Malformed/duplicate public CSV row")
            ids.add(row["row_id"])
    return len(ids)


def audit_ml(root, case, design_sha):
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("Prepared input must not use symlinks")
    summary = read(root / "summary.json")
    public = root / "public"
    bundle = read(public / "bundle_manifest.json")
    gate_path = root / "verifier/quality_gate.json"
    gate = read(gate_path)
    expected_public = {"bundle_manifest.json", "input/train.csv", "input/validation.csv", "input/test_features.csv"}
    if {p.relative_to(public).as_posix() for p in public.rglob("*") if p.is_file()} != expected_public:
        raise ValueError("Unexpected file in candidate-facing preparation")
    if (summary["case_id"] != case["case_id"] or bundle["case_id"] != case["case_id"]
            or gate["case_id"] != case["case_id"] or gate["design_sha256"] != design_sha
            or bundle["design_sha256"] != design_sha or summary["paid_execution_allowed"]
            or bundle["hidden_labels_included"] or not summary["no_provider_calls"]
            or gate["excluded_features"] != case["excluded_features"]
            or bundle["excluded_features"] != case["excluded_features"]):
        raise ValueError("Preparation identity or no-execution guard changed")
    if (sha256(gate_path) != summary["quality_gate_sha256"]
            or sha256(root / "verifier/trusted_reference_predictions.csv") != gate["reference_predictions_sha256"]
            or sha256(MAJOR / "reference_ml_gates.py") != gate["reference_script_sha256"]
            or sha256(HERE / "prepare_ml_case.py") != gate["preparation_script_sha256"]
            or sha256(MAJOR / "ml_cases/hidden" / case["corpus"] / "test_labels.csv") != gate["hidden_labels_sha256"]):
        raise ValueError("Prepared reference/labels/script identity changed")
    counts = {}
    for name in ("train", "validation", "test_features"):
        path = public / "input" / (name + ".csv")
        digest = sha256(path)
        if digest != summary["public_input_sha256"][name] or digest != bundle["public_input_sha256"][name]:
            raise ValueError("Prepared public input identity changed")
        counts[name] = audit_public_csv(path, development=name != "test_features", excluded=case["excluded_features"])
    if counts != summary["rows"] or counts["train"] < case["minimum_train_rows"]:
        raise ValueError("Prepared row accounting changed")
    return {"case_id": case["case_id"], "rows": counts, "quality_gate_sha256": sha256(gate_path),
            "not_an_llm_observation": True, "container_preflight_pending": True}


def audit_dry(path):
    summary = read(path / "summary.json")
    if summary["research_results"] or not summary["no_provider_calls"] or len(summary["runs"]) != 20:
        raise ValueError("Dry checks cannot be promoted to research results")
    seen = set()
    for row in summary["runs"]:
        signature = (row["scenario"], row["policy"])
        if signature in seen:
            raise ValueError("Duplicate fixture run")
        seen.add(signature)
        belt = fixture_run(row["policy"], row["scenario"])
        if row != {"policy": row["policy"], "scenario": row["scenario"], **belt.accounting()}:
            raise ValueError("Fixture summary differs from trusted replay")
        lines = (path / ("_".join(signature) + ".jsonl")).read_text(encoding="utf-8").splitlines()
        if [json.loads(line) for line in lines] != belt.events:
            raise ValueError("Fixture ledger differs from trusted replay")
    return {"fixture_runs": len(seen), "replayed_ledgers_match": True, "research_results": False}


def audit_processes(path):
    result = read(path)
    if (result["research_results"] or not result["no_provider_calls"] or not result["same_proposals"]
            or len(set(result["local_agent_process_ids"])) != 4
            or sha256(HERE / "decision_worker.py") != result["worker_sha256"]):
        raise ValueError("Recorded trusted decision check failed identity/placement guards")
    return {"separate_agent_processes_recorded": 4, "central_decision_processes_recorded": 1,
            "same_proposals": True, "not_a_live_or_latency_result": True}


def audit_claims(path):
    result = read(path / "summary.json")
    if result["research_results"] or not result["no_provider_calls"]:
        raise ValueError("Claim fixture cannot be a live result")
    for name, digest in result["implementation_sha256"].items():
        if Path(name).name != name or sha256(HERE / name) != digest:
            raise ValueError("Recorded claim implementation identity changed")
    for label in ("same_task", "same_agent"):
        row = result[label]
        if row["winner_count"] != 1 or len(set(row["worker_process_ids"])) != row["workers"]:
            raise ValueError("Recorded cross-process claim invariant failed")
        db_path = (path / (label + ".db")).resolve()
        with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as db:
            tasks = [list(r) for r in db.execute("SELECT id,state,owner,attempts FROM tasks ORDER BY id")]
            agents = [list(r) for r in db.execute("SELECT id,busy_task FROM agents ORDER BY id")]
            events = [{"sequence": s, "monotonic_ns": t, "event": e, **json.loads(p)}
                      for s, t, e, p in db.execute("SELECT seq,monotonic_ns,event,payload FROM events ORDER BY seq")]
        if tasks != row["task_states"] or agents != row["agent_states"] or events != row["claim_events"]:
            raise ValueError("Recorded claim store differs from its saved evidence")
        if sum(e["event"] == "claim_win" for e in events) != 1:
            raise ValueError("Claim ledger has more than one winner")
    return {"same_task_winners": 1, "same_agent_winners": 1,
            "single_host_correctness_only": True, "shared_store_failure_domain_remains": True}


def audit():
    identity = audit_design()
    design = read(DEST / "design.json")
    cases = {c["case_id"]: c for c in design["ml_specifications"]}
    prepared, incomplete = [], []
    preparation_root = HERE / "ml_preparation"
    if preparation_root.exists():
        for root in sorted(preparation_root.iterdir()):
            if not root.is_dir() or root.name not in cases:
                raise ValueError("Unexpected preparation case")
            if not (root / "summary.json").is_file():
                incomplete.append(root.name)
                continue
            prepared.append(audit_ml(root, cases[root.name], identity["design_sha256"]))
    fixtures = {}
    if (HERE / "dry_checks_20261006/summary.json").exists():
        fixtures["logical_belt"] = audit_dry(HERE / "dry_checks_20261006")
    if (HERE / "decision_process_check_20261006.json").exists():
        fixtures["decision_placement"] = audit_processes(HERE / "decision_process_check_20261006.json")
    if (HERE / "shared_claim_check_20261006/summary.json").exists():
        fixtures["shared_cas"] = audit_claims(HERE / "shared_claim_check_20261006")
    return {"status": "offline_preparation_audited_not_live_ready", "research_results": False,
            "no_provider_calls": True, "paid_execution_allowed": False, "live_ready": False,
            "design_sha256": identity["design_sha256"], "prepared_ml": prepared,
            "incomplete_preparations": incomplete, "fixture_checks": fixtures,
            "remaining_gates": ["budget_sample_size_precision_freeze", "new_container_references",
                                "new_repository_preflight_and_gold_free_identity",
                                "ecological_calibration_and_ability_profile_uncertainty",
                                "difficulty_label_provenance", "live_assessor_executor_verifier_integration",
                                "end_to_end_decision_clock_claim_path", "approval_quota"]}


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
