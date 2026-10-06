"""Select BugsInPy pilot cases from ordered, pre-LLM environment preflights.

This module does not execute a repository, apply a patch, or call an LLM.
Preflight records must be consecutive in the frozen metadata order; a skipped
candidate cannot silently disappear from the selection denominator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "bugsinpy_candidate_manifest.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _can_finish(chosen: list[dict], remaining: list[dict], size: int, repos: int) -> bool:
    slots = size - len(chosen)
    if slots < 0 or len(remaining) < slots:
        return False
    existing = {item["project"] for item in chosen}
    new = {item["project"] for item in remaining} - existing
    return len(existing) + min(slots, len(new)) >= repos


def earliest_diverse_subset(eligible: list[dict], size: int = 6, repos: int = 3) -> list[dict]:
    """Lexicographically earliest size-N subsequence with repo diversity."""
    if not _can_finish([], eligible, size, repos):
        raise ValueError("insufficient eligible cases or repository diversity")
    chosen: list[dict] = []
    for index, item in enumerate(eligible):
        if len(chosen) == size:
            break
        trial = chosen + [item]
        if _can_finish(trial, eligible[index + 1:], size, repos):
            chosen = trial
    if len(chosen) != size or len({item["project"] for item in chosen}) < repos:
        raise AssertionError("deterministic diverse-subset selection failed")
    return chosen


def select(manifest_path: Path, ledger_path: Path, *, size: int = 6, repos: int = 3) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidates = manifest["candidates"]
    if manifest.get("status") != "metadata_only_not_preflighted":
        raise ValueError("candidate manifest is not the frozen metadata-only pool")
    records = []
    if ledger_path.is_file():
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    if len(records) > len(candidates):
        raise ValueError("more preflight records than candidates")
    eligible = []
    exclusions = []
    for index, record in enumerate(records):
        candidate = candidates[index]
        if any(record.get(key) != candidate[key] for key in (
            "selection_hash", "project", "bug_id"
        )):
            raise ValueError(f"preflight ledger skips or reorders candidate {index}")
        if record.get("status") == "reproducible":
            if (
                record.get("buggy_test_failed") is not True
                or record.get("fixed_test_passed") is not True
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(record.get("container_image_id")))
                or not re.fullmatch(r"[0-9a-f]{64}", str(record.get("buggy_test_report_sha256")))
                or not re.fullmatch(r"[0-9a-f]{64}", str(record.get("fixed_test_report_sha256")))
            ):
                raise ValueError(f"reproducible case lacks buggy/fixed evidence: {index}")
            eligible.append(candidate)
        elif record.get("status") == "environment_excluded":
            if not isinstance(record.get("reason"), str) or not record["reason"].strip():
                raise ValueError(f"environment exclusion lacks a reason: {index}")
            exclusions.append({
                "selection_hash": candidate["selection_hash"],
                "reason": record["reason"],
            })
        else:
            raise ValueError(f"invalid preflight status: {index}")
    chosen = []
    # Stop at the earliest consecutive preflight prefix that can support the
    # preregistered size and diversity. Later records are not used for choice.
    for end in range(1, len(eligible) + 1):
        prefix = eligible[:end]
        if len(prefix) >= size and len({item["project"] for item in prefix}) >= repos:
            chosen = earliest_diverse_subset(prefix, size, repos)
            break
    return {
        "status": "pilot_cases_selected" if chosen else "preflight_incomplete",
        "research_results": False,
        "no_llm_calls": True,
        "manifest_sha256": sha256(manifest_path),
        "ledger_sha256": sha256(ledger_path) if ledger_path.is_file() else None,
        "preflighted_in_frozen_order": len(records),
        "eligible_count": len(eligible),
        "exclusions": exclusions,
        "selected": [{
            "project": item["project"], "bug_id": item["bug_id"],
            "selection_hash": item["selection_hash"],
        } for item in chosen],
        "next_candidate": None if chosen or len(records) == len(candidates) else {
            "project": candidates[len(records)]["project"],
            "bug_id": candidates[len(records)]["bug_id"],
            "selection_hash": candidates[len(records)]["selection_hash"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--ledger", type=Path, default=HERE / "results" / "bugsinpy_preflight_ledger.jsonl")
    args = parser.parse_args()
    print(json.dumps(select(args.manifest, args.ledger), indent=2))


if __name__ == "__main__":
    main()
