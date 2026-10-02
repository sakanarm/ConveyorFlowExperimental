"""Freeze audited Real-LLM case bundles before observing policy outcomes."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
LOCK_PATH = HERE / "case_bundle_lock.json"
AUDIT_PATH = HERE / "case_bundle_audit.json"
MANIFEST_PATH = HERE / "case_manifest.csv"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    if audit.get("status") != "offline_case_bundle_audit_passed":
        raise ValueError("case bundle audit has not passed")
    if audit.get("case_count") != 60 or not all(audit.get("checks", {}).values()):
        raise ValueError("case bundle audit is incomplete")
    with MANIFEST_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 60 or any(row["executable_ready"].lower() != "true" for row in rows):
        raise ValueError("manifest does not contain 60 executable cases")
    case_hash_payload = json.dumps(
        lock["cases"], sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    lock.update(
        {
            "status": "FROZEN_FOR_EXECUTION",
            "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
            "manifest_sha256": sha256(MANIFEST_PATH),
            "audit_sha256": sha256(AUDIT_PATH),
            "case_files_merkle_sha256": hashlib.sha256(case_hash_payload).hexdigest(),
            "claim_boundary": {
                "adult_ml": "deterministic public-data microtasks",
                "beijing_ml": "deterministic public-data microtasks",
                "bugs2fix": "executable behavioral surrogates; not repository-level Java repair",
            },
        }
    )
    LOCK_PATH.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": lock["status"],
                "case_count": lock["case_count"],
                "manifest_sha256": lock["manifest_sha256"],
                "case_files_merkle_sha256": lock["case_files_merkle_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
