"""Seal small, credential-free capsules of v2.6 source preflight evidence.

Raw Podman logs remain on D:. These capsules give the reviewer hashes and
outcomes without mistaking public-test contrast for a completed repair case.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from build_prior_exposure_ledger_v1 import HERE


OUTPUT = HERE / "source_preflight_capsules_v1.json"
PHASES = (
    ("pysnooper_preflight_v1", "PySnooper", 0),
    ("pysnooper_preflight_v1b", "PySnooper", 2),
    ("sanic_preflight_v1", "sanic", 5),
    ("sanic_preflight_v1b", "sanic", 1),
    ("sanic_preflight_v1c", "sanic", 2),
)
RAW_BASE = (Path("D:/ConveyorFlowRuntime/v2_6") if os.name == "nt"
            else Path("/mnt/d/ConveyorFlowRuntime/v2_6"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build():
    phases = []
    for name, project, expected_count in PHASES:
        root = HERE / name
        queue, lock = read(root / "queue.json"), read(root / "lock.json")
        ledger = root / "ledger.jsonl"
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()
                if line.strip()] if ledger.exists() else []
        if len(rows) != expected_count or lock["provider_calls"] != 0:
            raise ValueError(f"Unexpected case count/provider call in {name}")
        case_rows = []
        for index, row in enumerate(rows):
            case = queue[index]
            case_id = f"{project}_{case['bug_id']}"
            path = RAW_BASE / name / f"{index:02d}_{case_id}/preflight_record.json"
            record = read(path)
            if (row["queue_index"] != index or row["case_id"] != case_id
                    or row["selection_hash"] != case["selection_hash"]
                    or row["record_sha256"] != sha(path)
                    or record["provider_calls"] != 0
                    or record["status"] != row["status"]):
                raise ValueError(f"Queue/record drift in {name}: {case_id}")
            case_rows.append({
                "case_id": case_id, "queue_index": index,
                "status": record["status"], "reason": record.get("reason"),
                "test_outcomes": record.get("test_outcomes"),
                "record_sha256": sha(path),
                "build_report_sha256": record["build_report_sha256"],
                "container_image_id": record.get("container_image_id"),
                "environment_deviation": record["environment_deviation"],
            })
        phases.append({
            "phase": name, "project": project,
            "lock_sha256": sha(root / "lock.json"),
            "queue_sha256": sha(root / "queue.json"),
            "config_sha256": sha(root / "config.json"),
            "ledger_sha256": sha(ledger) if ledger.exists() else None,
            "attempted_cases": len(case_rows),
            "qualified_public_test_contrasts": sum(
                row["status"] == "reproducible" for row in case_rows),
            "cases": case_rows,
        })
    return {
        "status": "pre_llm_source_preflight_capsules_not_main_results",
        "raw_artifacts_location": "D:/ConveyorFlowRuntime/v2_6",
        "raw_artifacts_required_for_full_independent_audit": True,
        "provider_calls": 0,
        "phases": phases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = build()
    if args.write:
        serialized = json.dumps(result, indent=2, sort_keys=True,
                                ensure_ascii=False) + "\n"
        if OUTPUT.exists():
            if OUTPUT.read_text(encoding="utf-8") != serialized:
                raise ValueError("Sealed preflight capsule drift")
        else:
            with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(serialized)
    print(json.dumps({"status": result["status"],
                      "phases": len(result["phases"]),
                      "attempted_cases": sum(row["attempted_cases"]
                                             for row in result["phases"]),
                      "provider_calls": 0}))


if __name__ == "__main__":
    main()
