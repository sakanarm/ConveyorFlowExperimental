"""Prepare and certify public-only isolated probes; NO provider calls."""
import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from materialize_ml_bundle import materialize
from run_ml_dag_stage import ARTIFACT, PREDECESSOR, SCRIPT, STAGES, sha256
from run_ml_dag_llm_feasibility import preflight_container
from ml_stage_probe_sandbox_v1 import run_named_stage, verify_artifact

HERE = Path(__file__).resolve().parent
ROOT = HERE / "candidate_workspaces/ml_isolated_stage_v1_preparation"
CASES = ("ADULT_P1", "BEIJING_P1", "ADULT_P2")


def write(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")


def clone_probe(case_id, stage, output):
    reference = HERE / "candidate_workspaces" / (case_id + "_trusted_dag_smoke_podmanr02")
    materialize(case_id, output)
    for previous in PREDECESSOR[stage]:
        report = json.loads((reference / "dag_output" / previous / "stage_report.json").read_text())
        artifact = reference / "dag_output" / previous / ARTIFACT[previous]
        if not report["verified"] or report["artifact_sha256"] != sha256(artifact):
            raise ValueError("trusted predecessor provenance failed")
        shutil.copy2(reference / "submission" / SCRIPT[previous], output / "submission" / SCRIPT[previous])
        shutil.copytree(reference / "dag_output" / previous, output / "dag_output" / previous)
    return reference


def evidence_files(bundle):
    return {p.relative_to(bundle).as_posix(): sha256(p) for p in bundle.rglob("*") if p.is_file()}


def prepare():
    if sys.platform != "linux" or os.environ.get("CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("trusted preparation must run on Linux Podman")
    if ROOT.exists():
        raise FileExistsError("preparation exists; preserve and audit, never overwrite")
    # Avoid calling reused cases a new task specification.
    exposed = []
    for path in (HERE / "candidate_workspaces").rglob("*request_started*.json"):
        try:
            record = json.loads(path.read_text())
        except (ValueError, UnicodeError):
            continue
        if record.get("case_id") in CASES:
            exposed.append(path.as_posix())
    if exposed:
        raise ValueError("planned ML specification already has model request evidence: " + str(exposed))
    ready = preflight_container()
    ROOT.mkdir()
    write(ROOT / "preparation_started.json", {"created_at_utc": datetime.now(timezone.utc).isoformat(),
          "case_ids": CASES, "provider_calls": 0, "container_preflight": ready,
          "runner_sha256": sha256(Path(__file__)), "sandbox_sha256": sha256(HERE / "ml_stage_probe_sandbox_v1.py"),
          "verifier_sha256": sha256(HERE / "ml_stage_probe_verifier_v1.py"),
          "protocol_sha256": sha256(HERE / "ML_ISOLATED_STAGE_PILOT_V1_PROTOCOL_TH.md")})
    rows = []
    for case_id in CASES:
        for stage in STAGES:
            bundle = ROOT / (case_id + "_" + stage)
            reference = clone_probe(case_id, stage, bundle)
            shutil.copy2(reference / "submission" / SCRIPT[stage], bundle / "submission" / SCRIPT[stage])
            execution = run_named_stage(case_id, bundle, stage, "trusted_preflight")
            compatibility = verify_artifact(case_id, bundle, stage, "trusted_preflight") if execution["verified"] and stage in {"preprocess", "train"} else None
            passed = execution["verified"] and (compatibility is None or compatibility["verified"])
            row = {"case_id": case_id, "stage": stage, "verified": passed,
                   "provider_calls": 0, "reference_only_not_llm_observation": True,
                   "bundle": bundle.relative_to(HERE).as_posix(), "file_sha256": evidence_files(bundle)}
            write(bundle / "preparation_summary.json", row)
            rows.append(row)
            print(json.dumps({"case_id": case_id, "stage": stage, "trusted_reference_verified": passed}), flush=True)
            if not passed:
                write(ROOT / "stopped_summary.json", {"status": "preparation_stopped_before_provider_calls", "rows": rows})
                raise ValueError("trusted reference failed new named/semantic probe gate")
    result = {"status": "isolated_stage_reference_preparation_passed", "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "provider_calls": 0, "probe_count": 12, "source_corpora": 2,
              "not_probability_fit": True, "not_allocation_comparison": True, "rows": rows}
    write(ROOT / "summary.json", result)
    return result


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    r = prepare()
    print(json.dumps({k: v for k, v in r.items() if k != "rows"}, indent=2))
