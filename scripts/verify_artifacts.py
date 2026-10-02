from __future__ import annotations

import csv
import argparse
import gzip
import hashlib
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def gzip_sha256(path_text: str) -> tuple[str, str]:
    path = Path(path_text)
    digest = hashlib.sha256()
    with gzip.open(path, "rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return path.name.removesuffix(".jsonl.gz"), digest.hexdigest()


def source_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted((ROOT / "Code" / "conveyorflow_v2").glob("*.py")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "results" / "pilot"))
    args = parser.parse_args()
    output = Path(args.output)
    with (output / "metrics.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        metrics = list(csv.DictReader(handle))
    with (output / "design.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        design = list(csv.DictReader(handle))
    expected_hash = {row["run_id"]: row["event_hash"] for row in metrics}
    paths = sorted((output / "events").glob("*.jsonl.gz"))
    mismatches: list[dict] = []
    with ProcessPoolExecutor(max_workers=min(8, os.cpu_count() or 1)) as executor:
        for run_id, observed in executor.map(gzip_sha256, map(str, paths), chunksize=8):
            expected = expected_hash.get(run_id)
            if observed != expected:
                mismatches.append(
                    {"run_id": run_id, "expected": expected, "observed": observed}
                )
    metadata = json.loads((output / "run_metadata.json").read_text(encoding="utf-8"))
    design_ids = {
        row.get("run_id")
        or (
            f"{row['strategy']}__{row['team']}__{row['workload']}__"
            f"{row['load_name']}__{row['resource_regime']}__s{int(row['seed']):02d}"
        )
        for row in design
    }
    metric_ids = set(expected_hash)
    report = {
        "status": "pass" if not mismatches and design_ids == metric_ids else "fail",
        "design_rows": len(design),
        "metric_rows": len(metrics),
        "event_files": len(paths),
        "unique_design_ids": len(design_ids),
        "unique_metric_ids": len(metric_ids),
        "design_metric_id_sets_equal": design_ids == metric_ids,
        "event_hashes_checked": len(paths),
        "event_hash_mismatches": mismatches,
        "metadata_source_sha256": metadata["source_sha256"],
        "current_source_sha256": source_hash(),
        "source_hash_matches": metadata["source_sha256"] == source_hash(),
    }
    if not report["source_hash_matches"]:
        report["status"] = "fail"
    (output / "artifact_verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
