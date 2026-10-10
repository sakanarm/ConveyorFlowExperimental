"""Freeze a FastAPI-only continuation queue after v1 exhaustion; no LLM calls."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex

import select_repair_cases_v1 as prior


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "cohort_v1b.json"
AMENDMENT = HERE / "PREFLIGHT_AMENDMENT_V1B_TH.md"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def plan() -> dict:
    frozen = load(prior.OUTPUT)
    previous = load(prior.DESIGN)
    followup = load(prior.FOLLOWUP)
    exposed = {(p, str(b)) for p, b in previous["excluded_repository_cases"]}
    exposed.update((c["project"], str(c["bug_id"]))
                   for c in previous["repository_preflight_pool"])
    exposed.update((case_id.rsplit("_", 1)[0], case_id.rsplit("_", 1)[1])
                   for case_id in followup["planned_case_ids"])
    eligible = []
    for case in load(prior.SOURCE)["candidates"]:
        bug_id = str(case["bug_id"])
        if (case["project"] != "fastapi" or ("fastapi", bug_id) in exposed
                or not case["python_version"].startswith("3.8.")):
            continue
        metadata = prior.V2 / "bip/projects/fastapi/bugs" / bug_id
        script = metadata / "run_test.sh"
        if not script.is_file() or sha256(script) != case["run_test_sha256"]:
            continue
        command = shlex.split(script.read_text(encoding="utf-8").strip())
        if (len(command) != 2 or command[0] != "pytest"
                or not command[1].startswith(case["test_file"] + "::")
                or sha256(metadata / "bug.info") != case["bug_info_sha256"]):
            continue
        key = hashlib.sha256(
            f"{prior.SELECTION_DOMAIN}|fastapi|{bug_id}".encode()).hexdigest()
        eligible.append((key, {
            "case_id": f"fastapi_{bug_id}", "project": "fastapi", "bug_id": bug_id,
            "selection_hash": key, "python_version": case["python_version"],
            "test_file": case["test_file"], "visible_test": command[1],
            "run_test_sha256": case["run_test_sha256"],
            "bug_info_sha256": case["bug_info_sha256"],
            "buggy_commit_id": case["buggy_commit_id"],
            "fixed_commit_id_for_validator_only": case["fixed_commit_id_for_validator_only"],
        }))
    eligible.sort(key=lambda pair: pair[0])
    original = frozen["queues"]["fastapi"]
    if [(key, row["case_id"]) for key, row in eligible[:len(original)]] != [
        (row["selection_hash"], row["case_id"]) for row in original
    ]:
        raise ValueError("Original FastAPI prefix no longer matches metadata")
    reserve = [row | {"queue_index": len(original) + i}
               for i, (_, row) in enumerate(eligible[len(original):])]
    if not reserve:
        raise ValueError("No metadata-qualified FastAPI reserve")
    return {
        "status": "pre_provider_outcome_blind_fastapi_reserve",
        "selection_domain": prior.SELECTION_DOMAIN,
        "original_fastapi_prefix_count": len(original),
        "target_fastapi_reproducible_total": prior.TARGET_PER_PROJECT,
        "reserve_queue": reserve,
        "dependencies_sha256": {
            "selector": sha256(Path(__file__)), "amendment": sha256(AMENDMENT),
            "cohort_v1": sha256(prior.OUTPUT), "preflight_v1_ledger": sha256(
                HERE / "results/preflight_v1/ledger.jsonl"),
            "source_manifest": sha256(prior.SOURCE),
            "prior_design": sha256(prior.DESIGN),
            "prior_followup_lock": sha256(prior.FOLLOWUP),
        },
        "provider_calls": 0, "paid_execution_allowed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--freeze", action="store_true")
    actions.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    planned = plan()
    if args.freeze:
        if OUTPUT.exists():
            raise FileExistsError("Reserve cohort already frozen")
        planned["created_at_utc"] = datetime.now(timezone.utc).isoformat()
        with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(planned, stream, indent=2, sort_keys=True)
            stream.write("\n")
    elif (frozen := load(OUTPUT)) != planned | {
            "created_at_utc": frozen["created_at_utc"]}:
        raise ValueError("Reserve cohort drift")
    print(json.dumps({"status": "frozen" if args.freeze else "audited",
                      "reserve_cohort_sha256": sha256(OUTPUT),
                      "reserve_case_ids": [c["case_id"] for c in planned["reserve_queue"]],
                      "provider_calls": 0}))


if __name__ == "__main__":
    main()
