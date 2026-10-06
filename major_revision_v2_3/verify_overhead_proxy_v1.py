"""Read-only integrity and recomputation check for the local IPC proxy."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from measure_overhead_proxy_v1 import CONFIG, HERE, RESULTS, sha256, summarize


def verify(result_dir: Path = RESULTS / "main") -> dict:
    result_dir = result_dir.resolve()
    manifest = json.loads((result_dir / "manifest.json").read_text(encoding="utf-8"))
    settings = json.loads(CONFIG.read_text(encoding="utf-8"))
    csv_path = result_dir / "paired_latency.csv"
    if (
        manifest.get("status") != "single_host_serial_ipc_proxy_measured"
        or manifest.get("pairs") != settings["main_pairs"]
        or manifest.get("not_provider_latency") is not True
        or manifest.get("not_real_outage_evidence") is not True
    ):
        raise ValueError("overhead proxy manifest is not the frozen main measurement")
    for label, path in {
        "config": CONFIG,
        "runner": HERE / "measure_overhead_proxy_v1.py",
        "paired_latency": csv_path,
    }.items():
        if sha256(path) != manifest["sha256"][label]:
            raise ValueError(f"overhead proxy artifact changed: {label}")
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != settings["main_pairs"]:
        raise ValueError("overhead proxy pair count changed")
    parsed = []
    for index, row in enumerate(rows):
        if int(row["pair_id"]) != index or row["first_route"] not in {"local", "central"}:
            raise ValueError("overhead proxy pair order changed")
        parsed.append({
            "pair_id": index,
            "first_route": row["first_route"],
            "local_ms": float(row["local_ms"]),
            "central_ms": float(row["central_ms"]),
            "central_minus_local_ms": float(row["central_minus_local_ms"]),
        })
    recomputed = summarize(parsed, seed=settings["seed"])
    for label, value in recomputed.items():
        if manifest[label] != value:
            raise ValueError(f"overhead proxy summary changed: {label}")
    return {
        "status": "overhead_proxy_verified",
        "pairs": len(parsed),
        "not_provider_latency": True,
        "manifest_sha256": sha256(result_dir / "manifest.json"),
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
