"""Audit exploratory ML-DAG pilots; never label them probability calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path, PureWindowsPath
from run_ml_dag_stage import execution_failure_class


HERE = Path(__file__).resolve().parent
CONFIG = HERE.parent / "real_llm_pilot" / "config.mfec_main_frozen.json"
STAGES = ("ingest", "preprocess", "train", "package")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def audit(root: Path) -> dict:
    root = root.resolve()
    config = _json(CONFIG)
    config_sha256 = sha256(CONFIG)
    models = {item["slot"]: item for item in config["models"]}
    summaries = sorted(root.glob("*_mfec_dag_feasibility/dag_summary.json"))
    if not summaries:
        raise ValueError("no completed DAG feasibility summaries found")
    cases = []
    reached: dict[str, dict[str, int]] = defaultdict(lambda: {"attempts": 0, "verified": 0})
    for summary_path in summaries:
        bundle = summary_path.parent.resolve()
        summary = _json(summary_path)
        if (
            summary.get("status") != "exploratory_real_llm_dag_feasibility_completed"
            or summary.get("research_results") is not False
            or summary.get("not_a_policy_comparison") is not True
            or PureWindowsPath(str(summary.get("bundle", ""))).name != bundle.name
            or summary.get("config_sha256") != config_sha256
        ):
            raise ValueError(f"not an eligible exploratory pilot: {summary_path}")
        model = models.get(summary.get("model_slot"))
        if model is None or model["model_id"] != summary.get("model_id"):
            raise ValueError(f"model slot/config mismatch: {summary_path}")
        stages = summary.get("stages")
        if not isinstance(stages, list) or len(stages) != summary.get("llm_calls"):
            raise ValueError(f"stage/call count mismatch: {summary_path}")
        if len(stages) > len(STAGES):
            raise ValueError("more calls than stages")
        totals = {"provider_reported_cost": 0.0, "input_tokens": 0, "output_tokens": 0}
        environment_unresolved = False
        for index, record in enumerate(stages):
            stage = record.get("stage")
            if stage != STAGES[index]:
                raise ValueError(f"DAG stage order mismatch: {summary_path}")
            metadata_path = bundle / f"dag_provider_{stage}.json"
            report_path = bundle / "dag_output" / stage / "stage_report.json"
            prompt_path = bundle / f"dag_prompt_{stage}.txt"
            response_path = bundle / f"dag_response_{stage}.txt"
            if (
                sha256(metadata_path) != record.get("provider_metadata_sha256")
                or sha256(report_path) != record.get("stage_report_sha256")
            ):
                raise ValueError(f"pilot evidence hash mismatch: {bundle}/{stage}")
            metadata = _json(metadata_path)
            report = _json(report_path)
            if (
                metadata.get("stage") != stage
                or metadata.get("prompt_sha256") != sha256(prompt_path)
                or metadata.get("response_sha256") != sha256(response_path)
                or report.get("case_id") != summary.get("case_id")
                or report.get("stage") != stage
                or report.get("verified") is not record.get("verified")
            ):
                raise ValueError(f"pilot evidence content mismatch: {bundle}/{stage}")
            provider = metadata.get("provider", {})
            environment_unresolved |= (report.get("failure_class") in {
                "container_start_failure", "execution_timeout_unresolved"}
                or execution_failure_class(report.get("execution", {})) in {
                    "container_start_failure", "execution_timeout_unresolved"})
            if not isinstance(provider, dict):
                raise ValueError("provider metadata missing")
            if provider.get("exact_model_version") != model["exact_version"]:
                raise ValueError(f"model version mismatch: {bundle}/{stage}")
            for key in totals:
                value = provider.get("response_cost" if key == "provider_reported_cost" else key)
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                    raise ValueError(f"invalid provider accounting: {key}")
                totals[key] += value
            cell = reached[stage]
            cell["attempts"] += 1
            cell["verified"] += int(record["verified"])
        expected = "ENVIRONMENT_UNRESOLVED" if environment_unresolved else (
            "VERIFIED" if len(stages) == 4 and all(item["verified"] for item in stages)
            else "DEAD_LETTER")
        if summary.get("job_outcome") != expected and not (
                environment_unresolved and summary.get("job_outcome") == "DEAD_LETTER"):
            raise ValueError(f"job outcome contradicts verified stages: {summary_path}")
        cases.append({
            "case_id": summary["case_id"], "model_id": summary["model_id"],
            "model_slot": summary["model_slot"],
            "prompt_revision": summary.get("prompt_revision", "legacy_unspecified"),
            "job_outcome": expected, "llm_calls": len(stages),
            "recorded_job_outcome": summary.get("job_outcome"),
            "classification_corrected_from_preserved_docker_exit_code": (
                summary.get("job_outcome") != expected),
            "stage_results": {item["stage"]: item["verified"] for item in stages},
            "stage_failure_classes": {
                item["stage"]: (
                    _json(bundle / "dag_output" / item["stage"] / "stage_report.json").get("failure_class")
                    or execution_failure_class(_json(bundle / "dag_output" / item["stage"] / "stage_report.json").get("execution", {}))
                    or "validator_failure")
                for item in stages if not item["verified"]
            },
            **totals, "summary_sha256": sha256(summary_path),
        })
    unclosed = []
    for bundle in sorted(root.glob("*_mfec_dag_feasibility")):
        if (bundle / "dag_summary.json").exists():
            continue
        providers = sorted(bundle.glob("dag_provider_*.json"))
        started = sorted(bundle.glob("dag_request_started_*.json"))
        if providers or started:
            unclosed.append({
                "bundle": bundle.name,
                "received_provider_responses": len(providers),
                "request_start_records": len(started),
                "response_evidence_sha256": {path.name: sha256(path) for path in providers},
                "requires_recovery_before_main_gate": True,
            })
    return {
        "status": "exploratory_pilot_evidence_audited",
        "research_results": False,
        "not_a_policy_comparison": True,
        "not_probability_calibration": True,
        "reason": "Small pilot sample; later DAG stages are conditional on predecessors passing.",
        "completed_pilot_jobs": len(cases),
        "audit_complete": not unclosed,
        "unclosed_provider_attempts": unclosed,
        "verified_full_jobs": sum(item["job_outcome"] == "VERIFIED" for item in cases),
        "environment_unresolved_jobs": sum(item["job_outcome"] == "ENVIRONMENT_UNRESOLVED" for item in cases),
        "reached_stage_counts": dict(reached),
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=HERE / "candidate_workspaces")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(audit(args.root), indent=2) + "\n"
    if args.output:
        destination = args.output.resolve()
        if not destination.is_relative_to((HERE / "results").resolve()):
            raise ValueError("audit output must stay inside v2.3/results")
        if destination.exists():
            raise FileExistsError("refusing to overwrite an existing audit")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(result, encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()
