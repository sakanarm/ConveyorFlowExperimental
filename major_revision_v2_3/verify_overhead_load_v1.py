"""Read-only integrity and summary verification for concurrent IPC sessions."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from measure_overhead_load_v1 import CONFIG, HERE, RESULTS, sha256, summarize


def verify(result_dir: Path = RESULTS / "main") -> dict:
    manifest_path = result_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    csv_path = result_dir / "sessions.csv"
    expected_sessions = (len(config["concurrent_clients"])
                         * config["repetitions_per_level"] * 2)
    if (manifest.get("status") != "single_host_ipc_load_proxy_measured"
            or manifest.get("sessions") != expected_sessions
            or manifest.get("not_provider_latency") is not True
            or manifest.get("not_real_outage_evidence") is not True):
        raise ValueError("not the frozen concurrent IPC main measurement")
    for label, path in {
        "config": CONFIG,
        "runner": HERE / "measure_overhead_load_v1.py",
        "sessions": csv_path,
    }.items():
        if sha256(path) != manifest["sha256"][label]:
            raise ValueError(f"load proxy artifact changed: {label}")
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != expected_sessions:
        raise ValueError("load proxy session count changed")
    parsed = []
    seen = set()
    for row in rows:
        clients = int(row["clients"])
        repetition = int(row["repetition"])
        route = row["route"]
        key = (clients, repetition, route)
        if (clients not in config["concurrent_clients"]
                or repetition not in range(config["repetitions_per_level"])
                or route not in {"local", "central"} or key in seen
                or int(row["requests"]) != clients * config["measured_requests_per_client"]):
            raise ValueError("invalid load proxy session cell")
        seen.add(key)
        parsed.append({
            "clients": clients,
            "repetition": repetition,
            "route": route,
            "requests": int(row["requests"]),
            "median_ms": float(row["median_ms"]),
            "p95_ms": float(row["p95_ms"]),
            "mean_ms": float(row["mean_ms"]),
        })
    for label, value in summarize(parsed, config).items():
        if manifest[label] != value:
            raise ValueError(f"load proxy summary changed: {label}")
    return {
        "status": "overhead_load_proxy_verified",
        "sessions": expected_sessions,
        "requests": sum(row["requests"] for row in parsed),
        "not_provider_latency": True,
        "manifest_sha256": sha256(manifest_path),
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
