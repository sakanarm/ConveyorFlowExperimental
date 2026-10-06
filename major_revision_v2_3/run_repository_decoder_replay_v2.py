"""Offline diagnostic replay of ALL v1 outputs; no provider calls or gold."""
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from audit_repository_repair_pilot_v1 import audit
from repository_patch_normalizer_v2 import normalize
from run_repository_repair_pilot_v1 import execute_patch, sha, save, dispositions

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config_repository_decoder_replay_v2.json"
LOCK = HERE / "repository_decoder_replay_v2_lock.json"
SOURCE = HERE / "candidate_workspaces/repository_repair_pilot_v1"
OUT = HERE / "candidate_workspaces/repository_decoder_replay_v2"


def freeze():
    source_audit = audit()
    if not source_audit["audit_complete"]:
        raise ValueError("source v1 audit is incomplete")
    inputs = {"config": sha(CONFIG), "runner": sha(Path(__file__)),
              "normalizer": sha(HERE / "repository_patch_normalizer_v2.py"),
              "source_auditor": sha(HERE / "audit_repository_repair_pilot_v1.py"),
              "source_lock": sha(HERE / "repository_repair_pilot_v1_lock.json")}
    evidence = {str(p.relative_to(SOURCE)): sha(p) for p in sorted(SOURCE.rglob("*.json"))}
    evidence.update({str(p.relative_to(SOURCE)): sha(p) for p in sorted(SOURCE.rglob("*.txt"))})
    if LOCK.exists():
        locked = json.loads(LOCK.read_text(encoding="utf-8"))
        if locked["inputs"] != inputs or locked["source_evidence"] != evidence:
            raise ValueError("decoder/source evidence changed after freeze")
        return locked
    locked = {"status": "diagnostic_frozen_before_test_replay", "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "inputs": inputs, "source_evidence": evidence, "settings": json.loads(CONFIG.read_text(encoding="utf-8")),
              "source_audit": source_audit, "provider_calls": 0, "research_results": False}
    save(LOCK, locked)
    return locked


def run():
    locked = freeze()
    original = json.loads((HERE / "repository_repair_pilot_v1_lock.json").read_text(encoding="utf-8"))
    timeout = locked["settings"]["execution_timeout_seconds"]
    OUT.mkdir()  # refuse replay overwrite
    rows = []
    for case in original["cases"]:
        case_id = case["case_id"]
        baseline = next(b for b in original["baseline_audit"]["cases"] if b["case_id"] == case_id)
        builds = HERE / "results/bugsinpy_candidate_v1" / case_id
        regression = json.loads((builds / "regression_selection.json").read_text(encoding="utf-8"))["nodeids"]
        expected_visible = {node: "passed" for node in dispositions(builds / "candidate_buggy_visible_files/tests.xml")}
        for slot in original["settings"]["model_slots"]:
            source_job = SOURCE / (case_id + "_" + slot)
            context = json.loads((source_job / "context.json").read_text(encoding="utf-8"))
            summary = json.loads((source_job / "summary.json").read_text(encoding="utf-8"))
            for record in summary["attempts"]:
                number = record["attempt"]
                source = source_job / ("attempt_" + str(number))
                directory = OUT / (case_id + "_" + slot + "_attempt_" + str(number))
                directory.mkdir()
                row = dict(case_id=case_id, model_slot=slot, original_attempt=number,
                           source_response_sha256=sha(source / "response.txt"),
                           source_provider_sha256=sha(source / "provider.json"),
                           lock_sha256=sha(LOCK), provider_calls=0)
                provider = json.loads((source / "provider.json").read_text(encoding="utf-8"))
                content = (source / "response.txt").read_text(encoding="utf-8")
                if provider["finish_reason"] != "stop" or not content:
                    row.update(status="UNRECOVERABLE_PROVIDER_OUTPUT", reason="non-stop or empty answer")
                else:
                    try:
                        answer = json.loads(content)
                        if set(answer) != {"patch"} or not isinstance(answer["patch"], str):
                            raise ValueError("JSON schema mismatch")
                        patch, metadata = normalize(answer["patch"], context["allowed_source_files"], case["allowed_files"])
                    except (ValueError, TypeError, KeyError) as error:
                        row.update(status="EXACT_CONTEXT_RECOVERY_REJECTED", reason=str(error))
                    else:
                        path = directory / "patch.diff"
                        path.write_bytes(patch)
                        save(directory / "metadata_changes.json", metadata)
                        row["canonical_patch_sha256"] = sha(path)
                        visible = execute_patch(path, case, baseline, "visible", [case["visible_test"]], timeout)
                        if visible["execution"].get("timeout"):
                            row.update(status="EXECUTION_UNRESOLVED")
                        elif visible["execution"]["return_code"] != 0 or visible["dispositions"] != expected_visible:
                            row.update(status="VISIBLE_TEST_FAILED")
                        else:
                            checked = execute_patch(path, case, baseline, "regression", regression, timeout)
                            if checked["execution"].get("timeout"):
                                row.update(status="REGRESSION_UNRESOLVED")
                            elif checked["execution"]["return_code"] != 0 or checked["dispositions"] != baseline["dispositions"]:
                                row.update(status="WITHHELD_PUBLIC_REGRESSION_FAILED")
                            else:
                                repeat_visible = execute_patch(path, case, baseline, "replay_visible", [case["visible_test"]], timeout)
                                repeat_regression = execute_patch(path, case, baseline, "replay_regression", regression, timeout)
                                ok = (repeat_visible["execution"]["return_code"] == repeat_regression["execution"]["return_code"] == 0
                                      and repeat_visible["dispositions"] == expected_visible
                                      and repeat_regression["dispositions"] == baseline["dispositions"])
                                row.update(status="DIAGNOSTIC_REPAIR_VERIFIED" if ok else "CLEAN_REPLAY_UNRESOLVED")
                save(directory / "diagnostic_report.json", row)
                rows.append(row)
                print(json.dumps(row), flush=True)
    jobs = {(r["case_id"], r["model_slot"]) for r in rows if r["status"] == "DIAGNOSTIC_REPAIR_VERIFIED"}
    first = {(r["case_id"], r["model_slot"]) for r in rows if r["status"] == "DIAGNOSTIC_REPAIR_VERIFIED" and r["original_attempt"] == 1}
    result = {"status": "decoder_diagnostic_completed", "lock_sha256": sha(LOCK), "provider_calls": 0,
              "original_jobs": len(locked["source_audit"]["jobs"]), "original_attempts": len(rows),
              "attempt_statuses": dict(Counter(r["status"] for r in rows)),
              "first_original_attempt_recovered_jobs": len(first), "any_original_attempt_recovered_jobs": len(jobs),
              "research_results": False, "original_v1_outcomes_unchanged": True,
              "not_independent_new_model_jobs": True, "not_probability_calibration": True,
              "not_allocation_comparison": True, "rows": rows}
    save(OUT / "summary.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        print(json.dumps({"status": freeze()["status"], "provider_calls": 0}))
    elif args.execute:
        run()
    else:
        parser.error("choose --freeze or --execute")
