"""Independent read-only audit of v2.7 bounded Scrapy live allocation arms."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(V2 / "major_revision_v2_3/ecological_v1"))
from integration_backend_v1 import validate_ledger  # noqa: E402

LOCK = HERE / "scrapy_live_pair_v1/lock.json"
CANDIDATE = HERE / "scrapy_pair_v1b/candidate_lock.json"
RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_7/scrapy_live_pair_v1")
CAPSULE = HERE / "scrapy_live_pair_v1/audit_capsule_v1.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def inspect_arm(lock, case_id, arm, ids):
    root = RAW / case_id / arm
    summary_path = root / "allocation/summary.json"
    if not summary_path.is_file():
        return {"case_id": case_id, "arm": arm, "status": "INCOMPLETE"}
    events_path = root / "allocation/events.jsonl"
    validate_ledger(events_path)
    events = [json.loads(line) for line in events_path.read_text(
        encoding="utf-8").splitlines() if line.strip()]
    summary = read(summary_path)
    if (summary["lock_sha256"] != sha(LOCK) or summary["policy"] != arm or
            len(summary["task_states"]) != 1 or
            events[0]["event"] != "run_start" or
            events[0]["lock_sha256"] != sha(LOCK)):
        raise ValueError("Allocation lock/policy drift")
    decisions = [row for row in events if row["event"] == "agent_claim_component"]
    central = [row for row in events if row["event"] == "coordinator_choice"]
    if arm == "CF_FIT" and (not any(row["role"] == "agent" for row in decisions) or central):
        raise ValueError("CF-Fit decision actor evidence mismatch")
    if arm == "CENTRAL_RULE_MATCHED" and not central:
        raise ValueError("Central process choice missing")
    if arm == "STATIC_OWNERS" and central:
        raise ValueError("Static arm unexpectedly used coordinator fit choice")
    requests = list(root.glob("agent_*/request_started.json"))
    if len(requests) > 1:
        raise ValueError("More than one request for one arm")
    case = next(row for row in lock["cases"] if row["case_id"] == case_id)
    result = {"case_id": case_id, "arm": arm, "status": "COMPLETE",
              "allocation_summary_sha256": sha(summary_path),
              "event_ledger_sha256": sha(events_path),
              "task_state": next(iter(summary["task_states"].values())),
              "provider_request_markers": len(requests),
              "verified": 0}
    if not requests:
        return result
    marker_path = requests[0]
    marker = read(marker_path)
    job = marker_path.parent
    attempt_path = job / "summary.json"
    if not attempt_path.is_file():
        raise ValueError("Request started but attempt summary absent")
    attempt = read(attempt_path)
    if (marker["case_id"] != case_id or marker["arm"] != arm or
            marker["lock_sha256"] != sha(LOCK) or
            marker["prompt_sha256"] != case["prompt_sha256"] or
            marker["automatic_retry"] is not False or
            marker["model_slot"] != job.name):
        raise ValueError("Request marker drift")
    result.update(attempt_status=attempt["status"],
                  attempt_summary_sha256=sha(attempt_path),
                  model_slot=job.name)
    if (job / "provider.json").exists():
        provider = read(job / "provider.json")
        if (provider["provider_request_id"] != attempt["provider_request_id"] or
                provider["exact_model_version"] != attempt["returned_model_version"] or
                sha(job / "response.txt") != attempt["response_sha256"]):
            raise ValueError("Provider response identity/hash drift")
        if provider["provider_request_id"] in ids:
            raise ValueError("Duplicate provider request ID")
        ids.add(provider["provider_request_id"])
        result.update(provider_request_id=provider["provider_request_id"],
                      input_tokens=attempt["input_tokens"],
                      output_tokens=attempt["output_tokens"],
                      provider_cost_units_currency_unverified=attempt.get("response_cost_units"))
    if (job / "patch.diff").exists():
        if sha(job / "patch.diff") != attempt["patch_sha256"]:
            raise ValueError("Patch hash drift")
        for check in attempt["checks"]:
            report = job / (check["label"] + ".json")
            if sha(report) != check["report_sha256"] or read(report)["okay"] != check["okay"]:
                raise ValueError("Verifier report drift")
    if attempt["status"] == "VERIFIED":
        if (len(attempt["checks"]) != 4 or
                not all(check["okay"] for check in attempt["checks"]) or
                result["task_state"] != "VERIFIED"):
            raise ValueError("Verified claim without four passing checks")
        result["verified"] = 1
    elif result["task_state"] == "VERIFIED":
        raise ValueError("Verified task without passing attempt")
    return result


def independent_replay(case, patch, nodes):
    if not all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]+", node) for node in nodes):
        raise ValueError("Invalid frozen replay nodes")
    script = ("cp -a /buggy /tmp/work && cd /tmp/work && "
              "git apply --check /mnt/patch.diff && git apply /mnt/patch.diff && "
              "PYTHONPATH=/tmp/work python -m unittest -q " + " ".join(nodes))
    response = subprocess.run(
        ["podman", "run", "--rm", "--network", "none", "--read-only",
         "--cpus", "2", "--memory", "4g", "--pids-limit", "256",
         "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
         "--user", "65534:65534", "--tmpfs", "/tmp:rw,nosuid,size=2147483648",
         "--volume", str(patch) + ":/mnt/patch.diff:ro",
         case["validator_image"], "sh", "-c", script],
        capture_output=True, text=True, errors="replace", timeout=240)
    text = response.stdout + "\n" + response.stderr
    count = re.search(r"Ran (\d+) tests? in", text)
    if (response.returncode != 0 or count is None or int(count.group(1)) != len(nodes) or
            not re.search(r"(?:^|\n)OK(?:\n|$)", text) or "skipped=" in text):
        raise ValueError("Independent patch replay failed")
    return {"tests": int(count.group(1)),
            "transcript_sha256": hashlib.sha256(text.encode()).hexdigest()}


def audit(seal=False):
    lock = read(LOCK)
    if (lock["status"] != "v2_7_bounded_scrapy_live_pair_frozen" or
            lock["dependency_sha256"]["candidate_lock"] != sha(CANDIDATE) or
            lock["dependency_sha256"]["runner"] != sha(HERE / "run_scrapy_live_pair_v1.py")):
        raise ValueError("Frozen experiment dependency drift")
    ids = set()
    arms = [inspect_arm(lock, case_id, arm, ids)
            for case_id, arm in lock["execution_order"]]
    complete = all(row["status"] == "COMPLETE" for row in arms)
    result = {
        "status": "SIX_ARMS_INDEPENDENTLY_AUDITED_BOUNDED_ONE_REPOSITORY" if complete
                  else "PARTIAL_ARMS_AUDITED_NOT_RESEARCH_RESULT",
        "lock_sha256": sha(LOCK),
        "candidate_lock_sha256": sha(CANDIDATE),
        "independent_repository_projects": 1,
        "not_main_mixed_cohort": True,
        "cases": 2,
        "arms_complete": sum(row["status"] == "COMPLETE" for row in arms),
        "provider_request_markers": sum(row.get("provider_request_markers", 0) for row in arms),
        "verified_jobs": {arm: sum(row["verified"] for row in arms
                               if row["status"] == "COMPLETE" and row["arm"] == arm)
                          for arm in ("CF_FIT", "CENTRAL_RULE_MATCHED", "STATIC_OWNERS")},
        "rows": arms,
    }
    if seal:
        if not complete or CAPSULE.exists():
            raise ValueError("Seal only complete, never-overwritten six-arm audit")
        for row in arms:
            if row.get("verified"):
                case = next(item for item in lock["cases"] if item["case_id"] == row["case_id"])
                patch = RAW / row["case_id"] / row["arm"] / row["model_slot"] / "patch.diff"
                row["independent_visible_replay"] = independent_replay(case, patch,
                                                                          case["visible_nodes"])
                row["independent_regression_replay"] = independent_replay(case, patch,
                                                                             case["regression_nodes"])
        result["sealed_at_utc"] = datetime.now(timezone.utc).isoformat()
        with CAPSULE.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, sort_keys=True, indent=2)
            stream.write("\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    print(json.dumps(audit(args.seal), sort_keys=True), flush=True)
