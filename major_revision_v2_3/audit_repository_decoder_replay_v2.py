"""Read-only verification of metadata recovery and actual container reports."""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from audit_repository_repair_pilot_v1 import audit, sha
from audit_repository_baselines_v2 import dispositions
from repository_patch_normalizer_v2 import normalize

HERE = Path(__file__).resolve().parent
ROOT = HERE / "candidate_workspaces/repository_decoder_replay_v2"


def check():
    original_audit = audit()
    source_lock = json.loads((HERE / "repository_repair_pilot_v1_lock.json").read_text(encoding="utf-8"))
    lock_path = HERE / "repository_decoder_replay_v2_linux_lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    for key, name in {"config": "config_repository_decoder_replay_v2.json", "runner": "run_repository_decoder_replay_v2.py",
                      "normalizer": "repository_patch_normalizer_v2.py", "source_auditor": "audit_repository_repair_pilot_v1.py",
                      "source_lock": "repository_repair_pilot_v1_lock.json"}.items():
        if sha(HERE / name) != lock["inputs"][key]:
            raise ValueError("decoder dependency changed: " + key)
    capsule = json.loads((HERE / "repository_decoder_replay_v2_linux_recovery.json").read_text(encoding="utf-8"))
    if sha(HERE / "run_repository_decoder_replay_v2_linux.py") != capsule["linux_wrapper_sha256"]:
        raise ValueError("platform wrapper changed")
    summary = json.loads((ROOT / "summary.json").read_text(encoding="utf-8"))
    rows = summary["rows"]
    expected = {(r["case_id"], r["model_slot"], n) for r in original_audit["jobs"] for n in range(1, r["provider_attempts"] + 1)}
    actual = {(r["case_id"], r["model_slot"], r["original_attempt"]) for r in rows}
    if expected != actual or len(rows) != len(actual) or summary["lock_sha256"] != sha(lock_path):
        raise ValueError("missing, duplicate or mismatched original attempt")
    records = []
    for row in rows:
        source = HERE / "candidate_workspaces/repository_repair_pilot_v1" / (row["case_id"] + "_" + row["model_slot"])
        attempt = source / ("attempt_" + str(row["original_attempt"]))
        output = ROOT / (source.name + "_attempt_" + str(row["original_attempt"]))
        if json.loads((output / "diagnostic_report.json").read_text(encoding="utf-8")) != row:
            raise ValueError("diagnostic report differs from summary")
        if sha(attempt / "response.txt") != row["source_response_sha256"] or sha(attempt / "provider.json") != row["source_provider_sha256"]:
            raise ValueError("source provider evidence changed")
        context = json.loads((source / "context.json").read_text(encoding="utf-8"))
        case = next(c for c in source_lock["cases"] if c["case_id"] == row["case_id"])
        baseline = next(c for c in source_lock["baseline_audit"]["cases"] if c["case_id"] == row["case_id"])
        provider = json.loads((attempt / "provider.json").read_text(encoding="utf-8"))
        artifact_hashes = {str(p.relative_to(output).as_posix()): sha(p) for p in output.rglob("*") if p.is_file()}
        if "canonical_patch_sha256" in row:
            answer = json.loads((attempt / "response.txt").read_text(encoding="utf-8"))
            canonical, _ = normalize(answer["patch"], context["allowed_source_files"], case["allowed_files"])
            if (output / "patch.diff").read_bytes() != canonical or sha(output / "patch.diff") != row["canonical_patch_sha256"]:
                raise ValueError("recovery changed addition/deletion or canonical metadata")
            visible = json.loads((output / "visible/execution.json").read_text(encoding="utf-8"))
            visible_dispositions = dispositions(output / "visible/reports/tests.xml")
            known = dispositions(HERE / "results/bugsinpy_candidate_v1" / row["case_id"] / "candidate_buggy_visible_files/tests.xml")
            expected_visible = {node: "passed" for node in known}
            if row["status"] == "VISIBLE_TEST_FAILED" and visible["return_code"] == 0 and visible_dispositions == expected_visible:
                raise ValueError("visible pass mislabeled as failure")
            if row["status"] == "DIAGNOSTIC_REPAIR_VERIFIED":
                for label in ("visible", "regression", "replay_visible", "replay_regression"):
                    directory = output / label
                    execution = json.loads((directory / "execution.json").read_text(encoding="utf-8"))
                    expected_nodes = expected_visible if "visible" in label else baseline["dispositions"]
                    if execution["return_code"] != 0 or dispositions(directory / "reports/tests.xml") != expected_nodes:
                        raise ValueError("verified repair has missing or failed test evidence")
        elif row["status"] == "UNRECOVERABLE_PROVIDER_OUTPUT":
            if provider["finish_reason"] == "stop" and (attempt / "response.txt").stat().st_size:
                raise ValueError("recoverable response mislabeled as unavailable")
        records.append({"case_id": row["case_id"], "model_slot": row["model_slot"], "original_attempt": row["original_attempt"],
                        "status": row["status"], "artifact_hashes": artifact_hashes})
    counts = dict(Counter(r["status"] for r in rows))
    if counts != summary["attempt_statuses"] or summary["provider_calls"] != 0:
        raise ValueError("summary accounting mismatch")
    jobs = {(r["case_id"], r["model_slot"]) for r in rows if r["status"] == "DIAGNOSTIC_REPAIR_VERIFIED"}
    if len(jobs) != summary["any_original_attempt_recovered_jobs"]:
        raise ValueError("duplicate attempts counted as independent jobs")
    return {"status": "offline_decoder_audit_passed", "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "decoder_lock_sha256": sha(lock_path), "summary_sha256": sha(ROOT / "summary.json"),
            "original_v1_jobs": original_audit["completed_jobs"], "original_v1_verified_jobs": original_audit["verified_jobs"],
            "diagnostic_attempt_statuses": counts, "unique_diagnostic_verified_jobs": len(jobs),
            "verified_cases": sorted(case for case, slot in jobs), "provider_calls_added": 0,
            "metadata_only_recovery_verified": True, "not_independent_new_jobs": True,
            "research_results": False, "records": records}


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
