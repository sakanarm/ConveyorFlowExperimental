"""Read-only metadata inventory for the prospective v2.6 repository frame.

This is not a case selection or a paid execution lock. It records why a
12-project target may or may not be attainable from the existing manifest.
"""

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
MANIFEST = V2 / "major_revision_v2_3/bugsinpy_candidate_manifest.json"
OUTPUT = HERE / "source_frame_inventory_v1.json"
DOMAIN = "ConveyorFlow-v2.6-project-frame-20261011"
PREVIOUS_LLM_PROJECTS = {
    "black", "fastapi", "luigi", "matplotlib", "pandas", "PySnooper"
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    groups = defaultdict(list)
    for case in manifest["candidates"]:
        groups[case["project"]].append(case)
    projects = []
    for project, cases in groups.items():
        versions = Counter(str(case["python_version"]).rsplit(".", 1)[0]
                           for case in cases)
        projects.append({
            "project": project,
            "public_candidate_cases": len(cases),
            "metadata_python_minor_counts": dict(sorted(versions.items())),
            "previous_real_llm_project_exposure": project in PREVIOUS_LLM_PROJECTS,
            "project_order_sha256": hashlib.sha256((DOMAIN + "|" + project).encode()).hexdigest(),
            "qualification_status": "not_assessed_by_v2_6",
        })
    projects.sort(key=lambda row: row["project_order_sha256"])
    if len(projects) != 17:
        raise ValueError("BugsInPy source frame no longer has 17 projects")
    return {
        "status": "metadata_inventory_not_a_frozen_main_cohort",
        "source_manifest_sha256": sha(MANIFEST),
        "selection_domain": DOMAIN,
        "target_distinct_qualified_projects": 12,
        "cases_per_qualified_project": 2,
        "max_possible_projects_in_this_frame": len(projects),
        "all_candidate_exclusions_must_be_logged": True,
        "no_llm_call_authorized_by_this_inventory": True,
        "projects": projects,
    }


if __name__ == "__main__":
    result = inventory()
    if OUTPUT.exists():
        if json.loads(OUTPUT.read_text(encoding="utf-8")) != result:
            raise ValueError("Source frame inventory drift")
    else:
        with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(json.dumps({"status": result["status"],
                      "projects": len(result["projects"]),
                      "previously_exposed_projects": sum(
                          row["previous_real_llm_project_exposure"]
                          for row in result["projects"])}))
