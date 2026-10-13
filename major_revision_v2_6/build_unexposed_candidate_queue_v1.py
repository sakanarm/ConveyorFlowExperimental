"""Freeze the metadata-only order for unexposed BugsInPy candidates.

This does not assert that any candidate passes container preflight. It records
all possible candidates, including exclusions, before qualification outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from build_prior_exposure_ledger_v1 import HERE, MANIFEST, OUTPUT as EXPOSURE


FRAME = HERE / "source_frame_inventory_v1.json"
OUTPUT = HERE / "unexposed_candidate_queue_v1.json"
DOMAIN = "ConveyorFlow-v2.6-case-queue-20261011"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build() -> dict:
    manifest = read(MANIFEST)
    frame = read(FRAME)
    ledger = read(EXPOSURE)
    if ledger["status"] != "complete_read_only_inventory" or ledger["errors"]:
        raise ValueError("Prior exposure inventory is incomplete")
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True,
        separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    if digest != ledger["source_manifest_canonical_sha256"] or digest != frame["source_manifest_canonical_sha256"]:
        raise ValueError("Source manifest and exposure ledger do not match")
    exposed = {row["name"].casefold() for row in ledger["exposures"]
               if row["kind"] == "repository_case"}
    by_project: dict[str, list[dict]] = {}
    for case in manifest["candidates"]:
        by_project.setdefault(case["project"], []).append(case)
    projects = []
    for project in frame["projects"]:
        name = project["project"]
        cases = []
        for case in by_project[name]:
            case_id = f"{name}_{case['bug_id']}"
            cases.append({
                "case_id": case_id,
                "prior_provider_exposure": case_id.casefold() in exposed,
                "preflight_status": "not_qualified_by_v2_6",
                "case_order_sha256": hashlib.sha256(
                    f"{DOMAIN}|{name}|{case['bug_id']}".encode("utf-8")).hexdigest(),
                "python_version_from_public_metadata": case["python_version"],
            })
        cases.sort(key=lambda row: row["case_order_sha256"])
        projects.append({
            "project": name,
            "project_order_sha256": project["project_order_sha256"],
            "candidate_count": len(cases),
            "prior_exposed_case_count": sum(row["prior_provider_exposure"] for row in cases),
            "unexposed_candidate_count": sum(not row["prior_provider_exposure"] for row in cases),
            "metadata_can_supply_two_unexposed_cases": sum(
                not row["prior_provider_exposure"] for row in cases) >= 2,
            "cases_in_frozen_hash_order": cases,
        })
    projects.sort(key=lambda row: row["project_order_sha256"])
    all_cases = {row["case_id"].casefold() for project in projects
                 for row in project["cases_in_frozen_hash_order"]}
    unknown_exposed = sorted(exposed - all_cases)
    if unknown_exposed:
        raise ValueError(f"Exposed cases absent from public candidate frame: {unknown_exposed}")
    return {
        "status": "metadata_queue_not_preflighted_not_main_cohort",
        "selection_domain": DOMAIN,
        "source_manifest_canonical_sha256": digest,
        "prior_exposure_ledger_sha256": hashlib.sha256(EXPOSURE.read_bytes()).hexdigest(),
        "projects_in_frame": len(projects),
        "projects_with_two_unexposed_metadata_candidates": sum(
            row["metadata_can_supply_two_unexposed_cases"] for row in projects),
        "target_qualified_projects": 12,
        "selection_rule": "Visit projects and their cases in recorded hash order; skip every prior-exposed case; preflight every examined candidate; accept first two passing cases per project; retain all exclusions and stop if fewer than 12 projects qualify.",
        "projects": projects,
        "v2_6_provider_calls_authorized": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = build()
    if args.write:
        serialized = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        if OUTPUT.exists():
            if OUTPUT.read_text(encoding="utf-8") != serialized:
                raise ValueError("Frozen metadata queue drift; do not overwrite")
        else:
            with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(serialized)
    print(json.dumps({"status": result["status"],
        "projects_in_frame": result["projects_in_frame"],
        "projects_with_two_unexposed_metadata_candidates":
            result["projects_with_two_unexposed_metadata_candidates"]}))


if __name__ == "__main__":
    main()
