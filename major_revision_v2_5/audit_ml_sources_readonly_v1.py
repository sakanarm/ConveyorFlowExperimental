"""Read-only identity check for v2.5 UCI archives; never downloads or repairs."""

from __future__ import annotations

import json
from pathlib import Path

import acquire_ml_sources_v1 as acquisition


def audit() -> dict:
    manifest = json.loads(acquisition.MANIFEST.read_text(encoding="utf-8"))
    if manifest["status"] != "sources_acquired_not_preflighted" or set(manifest["sources"]) != set(acquisition.SOURCES):
        raise ValueError("source inventory drift")
    if manifest["runner_sha256"] != acquisition.sha256(Path(acquisition.__file__)):
        raise ValueError("source acquisition script drift")
    for name, recorded in manifest["sources"].items():
        source = acquisition.RAW / f"{name}.zip"
        if not source.is_file() or source.stat().st_size != recorded["archive_bytes"]:
            raise ValueError(f"{name}: source archive absent or size changed")
        if acquisition.sha256(source) != recorded["sha256"]:
            raise ValueError(f"{name}: source archive hash changed")
        if acquisition.inspect_archive(source, name) != recorded["archive"]:
            raise ValueError(f"{name}: archive member inventory drift")
    return {"status": "read_only_source_identity_verified",
            "sources": len(manifest["sources"]), "provider_calls": 0,
            "manifest_sha256": acquisition.sha256(acquisition.MANIFEST)}


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
