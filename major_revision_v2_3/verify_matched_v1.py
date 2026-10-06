"""Read-only integrity check for the frozen v2.3 matched simulation."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from run_matched_v1 import CONFIG, HERE, RESULTS, ROOT
from conveyorflow_v2.workloads import llm_difficulty_path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def verify(result_dir: Path = RESULTS / "main") -> dict:
    result_dir = result_dir.resolve()
    manifest_path = result_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    settings = json.loads(CONFIG.read_text(encoding="utf-8"))
    expected_pairs = settings["expected_pairs"]
    if (
        manifest.get("status") != "completed_simulation"
        or manifest.get("research_results") is not True
        or manifest.get("pairs") != expected_pairs
        or manifest.get("runs") != 2 * expected_pairs
    ):
        raise ValueError("matched result manifest is incomplete or not a main run")
    sources = {
        "config": CONFIG,
        "runner": HERE / "run_matched_v1.py",
        "matched_engine": HERE / "matched_architecture.py",
        "original_simulator": ROOT / "Code" / "conveyorflow_v2" / "simulator.py",
        "difficulty_labels": llm_difficulty_path(ROOT, settings["difficulty_source"]),
        "metrics": result_dir / "metrics.csv",
        "pair_audit": result_dir / "pair_audit.csv",
    }
    for label, path in sources.items():
        if sha256(path) != manifest["sha256"][label]:
            raise ValueError(f"frozen matched artifact changed: {label}")
    pairs = rows(result_dir / "pair_audit.csv")
    metrics = rows(result_dir / "metrics.csv")
    if len(pairs) != expected_pairs or len(metrics) != 2 * expected_pairs:
        raise ValueError("matched result row counts changed")
    if len({row["pair_id"] for row in pairs}) != expected_pairs:
        raise ValueError("duplicate matched pair ID")
    by_pair: dict[str, set[str]] = {}
    for row in metrics:
        by_pair.setdefault(row["pair_id"], set()).add(row["strategy"])
    if set(by_pair) != {row["pair_id"] for row in pairs} or any(
        strategies != {"CF_FIT", "CENTRAL_MATCHED"} for strategies in by_pair.values()
    ):
        raise ValueError("matched policy arm is missing or duplicated")
    parity = [row for row in pairs if row["environment"] in {"E0", "E2_BELT"}]
    if len(parity) != manifest["parity_required_pairs"] or any(
        row["stream_equal"] != "True" or row["metrics_equal"] != "True"
        for row in parity
    ) or manifest["parity_failed_pairs"] != 0:
        raise ValueError("zero-overhead/shared-belt parity failed")
    analysis = result_dir / "analysis_overview.json"
    analysis_checked = False
    if analysis.exists():
        overview = json.loads(analysis.read_text(encoding="utf-8"))
        expected = overview["sha256"]
        if (
            sha256(manifest_path) != expected["raw_manifest"]
            or sha256(HERE / "analyze_matched_v1.py") != expected["analysis_script"]
            or sha256(result_dir / "summary.csv") != expected["summary_csv"]
        ):
            raise ValueError("matched analysis artifact changed")
        analysis_checked = True
    return {
        "status": "frozen_matched_results_verified",
        "simulation_only": True,
        "pairs": len(pairs), "runs": len(metrics),
        "parity_required_pairs": len(parity),
        "analysis_hashes_checked": analysis_checked,
        "manifest_sha256": sha256(manifest_path),
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
