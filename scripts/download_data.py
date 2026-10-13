from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "manifest.json"

SOURCES = [
    {
        "id": "adult",
        "url": "https://archive.ics.uci.edu/static/public/2/adult.zip",
        "path": RAW / "adult.zip",
        "license": "CC BY 4.0",
        "expected_records": 48_842,
    },
    {
        "id": "beijing",
        "url": "https://archive.ics.uci.edu/static/public/501/beijing%2Bmulti%2Bsite%2Bair%2Bquality%2Bdata.zip",
        "path": RAW / "beijing.zip",
        "license": "CC BY 4.0",
        "expected_records": 420_768,
    },
    {
        "id": "bugs2fix-small-buggy",
        "url": "https://raw.githubusercontent.com/microsoft/CodeXGLUE/main/Code-Code/code-refinement/data/small/train.buggy-fixed.buggy",
        "path": RAW / "bugs2fix" / "train.buggy.txt",
        "license": "C-UDA",
        "expected_records": 46_680,
    },
    {
        "id": "bugs2fix-small-fixed",
        "url": "https://raw.githubusercontent.com/microsoft/CodeXGLUE/main/Code-Code/code-refinement/data/small/train.buggy-fixed.fixed",
        "path": RAW / "bugs2fix" / "train.fixed.txt",
        "license": "C-UDA",
        "expected_records": 46_680,
    },
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path, force: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        return
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "ConveyorFlow-v2-research/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)
    temporary.replace(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    records = []
    for source in SOURCES:
        path = Path(source["path"])
        download(str(source["url"]), path, args.force)
        records.append(
            {
                "id": source["id"],
                "canonical_url": source["url"],
                "local_path": path.relative_to(ROOT).as_posix(),
                "license": source["license"],
                "expected_records": source["expected_records"],
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
        print(f"verified {source['id']}: {path.stat().st_size:,} bytes")
    payload = {
        "status": "downloaded_and_hashed",
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "redistribution_note": "Raw files are gitignored. CodeXGLUE data remains subject to C-UDA.",
        "datasets": records,
    }
    MANIFEST.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
