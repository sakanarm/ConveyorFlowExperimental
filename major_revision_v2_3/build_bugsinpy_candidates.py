"""Freeze metadata-only BugsInPy candidate order; never run repo code here."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
BENCHMARK = ROOT / "bip"
PINNED_COMMIT = "11c5f1eea954a42132cfd06bf257766a7963e0fd"
PILOT_SEED = "conveyorflow-v2.3-bugsinpy-pilot-20261003"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_info(path: Path) -> dict[str, str]:
    fields = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.fullmatch(r'([a-z_]+)\s*=\s*"(.*)"', line.strip())
        if match:
            fields[match.group(1)] = match.group(2)
    for required in ("buggy_commit_id", "fixed_commit_id", "test_file", "python_version"):
        if required not in fields:
            raise ValueError(f"missing {required} in {path}")
    return fields


def main() -> None:
    if not (BENCHMARK / "projects").is_dir():
        raise FileNotFoundError("BugsInPy metadata checkout is missing at v2/bip")
    observed_commit = subprocess.check_output(
        ["git", "-c", f"safe.directory={BENCHMARK.resolve().as_posix()}", "rev-parse", "HEAD"],
        cwd=BENCHMARK, text=True,
    ).strip()
    if observed_commit != PINNED_COMMIT:
        raise ValueError(f"BugsInPy source changed: {observed_commit}")
    pool = []
    for info_path in sorted((BENCHMARK / "projects").glob("*/bugs/*/bug.info")):
        bug_dir = info_path.parent
        project = info_path.parents[2].name
        bug_id = bug_dir.name
        fields = parse_info(info_path)
        run_test = bug_dir / "run_test.sh"
        if not run_test.is_file():
            continue
        pool.append({
            "project": project,
            "bug_id": bug_id,
            "buggy_commit_id": fields["buggy_commit_id"],
            "fixed_commit_id_for_validator_only": fields["fixed_commit_id"],
            "test_file": fields["test_file"],
            "python_version": fields["python_version"],
            "bug_info_sha256": sha256(info_path),
            "run_test_sha256": sha256(run_test),
            "preflight_status": "not_executed",
        })
    for item in pool:
        item["selection_hash"] = hashlib.sha256(
            f"{PILOT_SEED}|{item['project']}|{item['bug_id']}".encode("utf-8")
        ).hexdigest()
    ordered = sorted(pool, key=lambda item: item["selection_hash"])
    output = {
        "status": "metadata_only_not_preflighted",
        "research_results": False,
        "source_url": "https://github.com/soarsmu/BugsInPy",
        "source_commit": PINNED_COMMIT,
        "selection_seed": PILOT_SEED,
        "preflight_rule": (
            "In selection_hash order, require buggy relevant test to fail and fixed relevant"
            " test to pass in the same isolated container, then take the first six"
            " reproducible bugs spanning at least three repositories. Exclusions"
            " must be recorded before any LLM call."
        ),
        "all_metadata_candidates": len(ordered),
        "candidates": ordered,
    }
    path = HERE / "bugsinpy_candidate_manifest.json"
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": output["status"],
        "source_commit": PINNED_COMMIT,
        "all_metadata_candidates": len(ordered),
        "first_ten": [(item["project"], item["bug_id"]) for item in ordered[:10]],
    }, indent=2))


if __name__ == "__main__":
    main()
