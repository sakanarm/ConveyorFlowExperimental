"""Audit pre-v2.6 provider-start markers before selecting new main cases.

This scans only the named historical evidence roots. A request-start marker is
treated as exposure even when its response or verification later failed.
Nothing in this script authorizes a new provider call or selects a v2.6 case.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
V2 = HERE.parent
MANIFEST = V2 / "major_revision_v2_3/bugsinpy_candidate_manifest.json"
OUTPUT = HERE / "prior_exposure_ledger_v1.json"
ROOTS = {
    "v2_local_3": V2 / "major_revision_v2_3",
    "v2_local_4": V2 / "major_revision_v2_4",
    "v2_local_5": V2 / "major_revision_v2_5",
    "d_runtime_3": Path("D:/ConveyorFlowRuntime/v2_3"),
    "d_runtime_4": Path("D:/ConveyorFlowRuntime/v2_4"),
    "d_runtime_5": Path("D:/ConveyorFlowRuntime/v2_5"),
}
CORPORA = ("ADULT", "BEIJING", "BANK", "COVERTYPE")
KNOWN_UNLABELED_REPAIR = {
    "v25_black_llm_feasibility_v1": "black_3",
    "v25_pysnooper_llm_feasibility_v1": "PySnooper_3",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def marker_paths(root: Path):
    for directory, subdirs, files in os.walk(root):
        subdirs.sort()
        if "request_started.json" in files:
            yield Path(directory) / "request_started.json"


def identity(marker: dict, relative: Path, case_ids: dict[str, str]) -> tuple[str, str]:
    parts = [part.casefold() for part in relative.parts]
    explicit = marker.get("case_id") or marker.get("job_id")
    if explicit:
        value = str(explicit).casefold()
        if value in case_ids:
            return "repository_case", case_ids[value]
        for corpus in CORPORA:
            if corpus.casefold() in value:
                return "ml_corpus", corpus.lower()
        raise ValueError(f"Unrecognized explicit case/job identifier: {explicit}")

    for folder, case_id in KNOWN_UNLABELED_REPAIR.items():
        if folder.casefold() in parts:
            return "repository_case", case_id
    for part in parts:
        for case_key in sorted(case_ids, key=len, reverse=True):
            if part == case_key or part.startswith(case_key + "_agent_"):
                return "repository_case", case_ids[case_key]
    for part in parts:
        matches = [name.lower() for name in CORPORA if re.search(
            rf"(?:^|_){name.casefold()}(?:_|$)", part)]
        if len(matches) == 1:
            return "ml_corpus", matches[0]
    raise ValueError("No case/corpus identity in marker or path")


def build() -> dict:
    manifest_bytes = MANIFEST.read_bytes()
    manifest = json.loads(manifest_bytes)
    case_ids = {f"{case['project']}_{case['bug_id']}".casefold():
                f"{case['project']}_{case['bug_id']}"
                for case in manifest["candidates"]}
    if len(case_ids) != len(manifest["candidates"]):
        raise ValueError("Duplicate case ID in candidate manifest")

    exposures: dict[tuple[str, str], list[dict]] = defaultdict(list)
    roots = []
    errors = []
    for label, root in ROOTS.items():
        if not root.is_dir():
            roots.append({"label": label, "present": False, "markers": 0})
            errors.append(f"Historical evidence root absent: {label}")
            continue
        count = 0
        for path in marker_paths(root):
            count += 1
            relative = path.relative_to(root)
            try:
                raw = path.read_bytes()
                marker = json.loads(raw)
                kind, name = identity(marker, relative, case_ids)
                exposures[(kind, name)].append({
                    "evidence_root": label,
                    "relative_marker": relative.as_posix(),
                    "marker_sha256": sha256(raw),
                })
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"{label}/{relative.as_posix()}: {type(exc).__name__}: {exc}")
        roots.append({"label": label, "present": True, "markers": count})

    rows = []
    for (kind, name), markers in sorted(exposures.items()):
        rows.append({"kind": kind, "name": name,
                     "provider_start_markers": len(markers),
                     "evidence": sorted(markers, key=lambda row:
                                        (row["evidence_root"], row["relative_marker"]))})
    return {
        "status": "complete_read_only_inventory" if not errors else "incomplete_fail_closed",
        "rule": "Any provider request-start marker excludes that repository case from v2.6 main, regardless of outcome; ML exposure is recorded at corpus level and is not itself a corpus exclusion.",
        "source_manifest_canonical_sha256": sha256(json.dumps(
            manifest, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode("utf-8")),
        "roots": roots,
        "total_markers": sum(row["markers"] for row in roots),
        "repository_cases_exposed": sum(row["kind"] == "repository_case" for row in rows),
        "ml_corpora_exposed": sum(row["kind"] == "ml_corpus" for row in rows),
        "exposures": rows,
        "errors": errors,
        "v2_6_provider_calls_authorized": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Create immutable ledger if complete")
    args = parser.parse_args()
    result = build()
    if args.write:
        if result["errors"]:
            raise ValueError(f"Cannot freeze incomplete inventory: {len(result['errors'])} errors")
        serialized = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        if OUTPUT.exists():
            if OUTPUT.read_text(encoding="utf-8") != serialized:
                raise ValueError("Existing ledger drift; do not overwrite it")
        else:
            with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(serialized)
    print(json.dumps({key: result[key] for key in (
        "status", "total_markers", "repository_cases_exposed",
        "ml_corpora_exposed", "errors")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
