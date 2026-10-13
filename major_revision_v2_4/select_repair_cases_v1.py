"""Freeze an outcome-blind v2.4 BugsInPy candidate queue; no provider/container calls."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex


HERE = Path(__file__).resolve().parent
V2 = HERE.parent
PREVIOUS = V2 / "major_revision_v2_3"
PROJECTS = ("luigi", "matplotlib", "pandas", "fastapi")
SELECTION_DOMAIN = "ConveyorFlow-v2.4-repository-cohort-20261010"
QUEUE_LENGTH = 5
TARGET_PER_PROJECT = 3
SOURCE = PREVIOUS / "bugsinpy_candidate_manifest.json"
DESIGN = PREVIOUS / "ecological_v1/prepared_design/design.json"
FOLLOWUP = PREVIOUS / "ecological_v1/repository_repair_followup_execution_lock_v1.json"
PROTOCOL = HERE / "PROTOCOL_TH.md"
OUTPUT = HERE / "cohort_v1.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def plan() -> dict:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))["candidates"]
    previous = json.loads(DESIGN.read_text(encoding="utf-8"))
    followup = json.loads(FOLLOWUP.read_text(encoding="utf-8"))
    exposed = {(project, str(bug)) for project, bug in previous["excluded_repository_cases"]}
    exposed.update((case["project"], str(case["bug_id"]))
                   for case in previous["repository_preflight_pool"])
    exposed.update((case_id.rsplit("_", 1)[0], case_id.rsplit("_", 1)[1])
                   for case_id in followup["planned_case_ids"])
    queues: dict[str, list[dict]] = {}
    for project in PROJECTS:
        eligible = []
        for case in source:
            bug_id = str(case["bug_id"])
            if case["project"] != project or (project, bug_id) in exposed:
                continue
            if not case["python_version"].startswith("3.8."):
                continue
            metadata = V2 / "bip/projects" / project / "bugs" / bug_id
            script = metadata / "run_test.sh"
            if not script.is_file() or digest(script) != case["run_test_sha256"]:
                continue
            command = shlex.split(script.read_text(encoding="utf-8").strip())
            if (len(command) != 2 or command[0] != "pytest"
                    or not command[1].startswith(case["test_file"] + "::")):
                continue
            if digest(metadata / "bug.info") != case["bug_info_sha256"]:
                continue
            key = hashlib.sha256(
                f"{SELECTION_DOMAIN}|{project}|{bug_id}".encode()
            ).hexdigest()
            eligible.append((key, {
                "case_id": f"{project}_{bug_id}",
                "project": project,
                "bug_id": bug_id,
                "selection_hash": key,
                "python_version": case["python_version"],
                "test_file": case["test_file"],
                "visible_test": command[1],
                "run_test_sha256": case["run_test_sha256"],
                "bug_info_sha256": case["bug_info_sha256"],
                "buggy_commit_id": case["buggy_commit_id"],
                "fixed_commit_id_for_validator_only": case["fixed_commit_id_for_validator_only"],
            }))
        eligible.sort(key=lambda pair: pair[0])
        if len(eligible) < QUEUE_LENGTH:
            raise ValueError(f"Insufficient metadata-qualified unused cases: {project}")
        queues[project] = [record | {"queue_index": index}
                           for index, (_, record) in enumerate(eligible[:QUEUE_LENGTH])]
    all_ids = [row["case_id"] for queue in queues.values() for row in queue]
    if len(all_ids) != len(set(all_ids)):
        raise AssertionError("Duplicate case in queue")
    return {
        "status": "outcome_blind_candidate_queue_not_preflighted",
        "selection_domain": SELECTION_DOMAIN,
        "projects": list(PROJECTS),
        "target_per_project": TARGET_PER_PROJECT,
        "queue_length_per_project": QUEUE_LENGTH,
        "selection_rule": "First three pre-provider qualified in each fixed five-case queue; otherwise stop and amend before any paid call",
        "queues": queues,
        "dependencies_sha256": {
            "selector": digest(Path(__file__)), "protocol": digest(PROTOCOL),
            "source_manifest": digest(SOURCE), "prior_design": digest(DESIGN),
            "prior_followup_lock": digest(FOLLOWUP),
        },
        "prior_exposed_case_count": len(exposed),
        "provider_calls": 0,
        "paid_execution_allowed": False,
        "fastapi_environment_profile_ready": False,
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
            raise FileExistsError("Cohort already frozen; use --audit, never overwrite")
        planned["created_at_utc"] = datetime.now(timezone.utc).isoformat()
        with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(planned, stream, indent=2, sort_keys=True)
            stream.write("\n")
    else:
        frozen = json.loads(OUTPUT.read_text(encoding="utf-8"))
        for field, value in planned.items():
            if frozen.get(field) != value:
                raise ValueError(f"Frozen cohort drift: {field}")
    print(json.dumps({
        "status": "frozen" if args.freeze else "audited",
        "cohort_sha256": digest(OUTPUT),
        "projects": list(PROJECTS),
        "candidate_count": sum(len(queue) for queue in planned["queues"].values()),
        "target_cases_if_preflight_passes": len(PROJECTS) * TARGET_PER_PROJECT,
        "provider_calls": 0,
        "paid_execution_allowed": False,
    }))


if __name__ == "__main__":
    main()
