"""Acquire two additional public UCI corpora; no model calls or ML results.

The raw archives are deliberately excluded from Git.  This program never
replaces an existing source or manifest: a repeated invocation audits them.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile


HERE = Path(__file__).resolve().parent
ROOT = HERE / "new_ml_corpora_v1"
RAW = ROOT / "raw"
MANIFEST = ROOT / "source_manifest.json"
SOURCES = {
    "bank": {
        "url": "https://archive.ics.uci.edu/static/public/222/bank%2Bmarketing.zip",
        "doi": "10.24432/C5K306",
        "archive_member": "bank.zip",
        "expected_rows": 45_211,
        "max_download_bytes": 4_000_000,
        "task": "binary_classification",
        "license": "CC BY 4.0",
    },
    "covertype": {
        "url": "https://archive.ics.uci.edu/static/public/31/covertype.zip",
        "doi": "10.24432/C50K5N",
        "archive_member": "covtype.data.gz",
        "expected_rows": 581_012,
        "max_download_bytes": 30_000_000,
        "task": "multiclass_classification",
        "license": "CC BY 4.0",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_archive(path: Path, name: str) -> dict:
    with zipfile.ZipFile(path) as archive:
        members = archive.namelist()
        matches = [item for item in members if item.split("/")[-1] == SOURCES[name]["archive_member"]]
        if len(matches) != 1:
            raise ValueError(f"{name}: expected exactly one {SOURCES[name]['archive_member']}; found {matches}")
        member = archive.getinfo(matches[0])
        if member.file_size > 150_000_000:
            raise ValueError(f"{name}: unexpectedly large archive member")
        return {"member": matches[0], "member_bytes": member.file_size,
                "members": members}


def download_one(name: str) -> dict:
    item = SOURCES[name]
    RAW.mkdir(parents=True, exist_ok=True)
    destination = RAW / f"{name}.zip"
    partial = RAW / f"{name}.zip.part"
    if destination.exists():
        if partial.exists():
            raise FileExistsError(f"unexpected partial download: {partial}")
    else:
        if partial.exists():
            raise FileExistsError(f"interrupted download retained for audit: {partial}")
        request = urllib.request.Request(item["url"], headers={"User-Agent": "ConveyorFlow-reproducibility/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response, partial.open("xb") as target:
                total = 0
                while block := response.read(1 << 20):
                    total += len(block)
                    if total > item["max_download_bytes"]:
                        raise ValueError(f"{name}: download exceeded frozen byte cap")
                    target.write(block)
            inspect_archive(partial, name)
            partial.replace(destination)
        except Exception:
            # Preserve the partial file and error for a transparent recovery.
            raise
    return {"id": name, "url": item["url"], "doi": item["doi"],
            "license": item["license"], "task": item["task"],
            "expected_rows": item["expected_rows"], "archive_bytes": destination.stat().st_size,
            "sha256": sha256(destination), "archive": inspect_archive(destination, name)}


def audit() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["status"] != "sources_acquired_not_preflighted" or manifest["provider_calls"] != 0:
        raise ValueError("unexpected manifest state")
    if manifest["runner_sha256"] != sha256(Path(__file__)):
        raise ValueError("acquisition script changed after freeze")
    if set(manifest["sources"]) != set(SOURCES):
        raise ValueError("source set changed")
    for name, recorded in manifest["sources"].items():
        current = download_one(name)
        if current != recorded:
            raise ValueError(f"{name}: source identity drift")
    return {"status": "source_identity_verified_not_execution_ready",
            "sources": len(SOURCES), "provider_calls": 0,
            "manifest_sha256": sha256(MANIFEST)}


def acquire() -> dict:
    if MANIFEST.exists():
        return audit()
    records = {name: download_one(name) for name in SOURCES}
    manifest = {"status": "sources_acquired_not_preflighted",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "runner_sha256": sha256(Path(__file__)),
                "sources": records, "provider_calls": 0,
                "paid_execution_allowed": False,
                "note": "Dataset URLs and source identities only; splits, validators, and case cohort are not frozen."}
    ROOT.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return audit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    print(json.dumps(audit() if args.audit else acquire(), sort_keys=True))
