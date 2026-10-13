"""Describe held-out first-attempt LLM outcomes without fitting simulator priors.

The input is a frozen case/model manifest and an append-only JSONL ledger. This
script cannot turn microtask probes or conditional DAG pilots into ecological
success probabilities. A passed count gate still requires human methods review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
OUTCOMES = {"verified", "model_failed", "provider_failed", "environment_invalid"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wilson(successes: int, trials: int) -> tuple[float | None, float | None]:
    if trials == 0:
        return None, None
    z = 1.959963984540054
    rate = successes / trials
    denominator = 1 + z * z / trials
    center = (rate + z * z / (2 * trials)) / denominator
    half = z * math.sqrt(
        rate * (1 - rate) / trials + z * z / (4 * trials * trials)
    ) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def summarize(manifest_path: Path, ledger_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "held_out_ecological_calibration_frozen":
        raise ValueError("manifest must be frozen before calibration outcomes")
    models = {item["slot"]: item for item in manifest["models"]}
    probes = {item["probe_id"]: item for item in manifest["probes"]}
    if len(models) != len(manifest["models"]) or len(probes) != len(manifest["probes"]):
        raise ValueError("duplicate model slot or probe ID")
    workloads = manifest["workloads"]
    difficulties = manifest["difficulties"]
    if (
        not models or not probes or not workloads or difficulties != [1, 2, 3]
        or len(set(workloads)) != len(workloads)
        or not isinstance(manifest.get("min_scored_per_cell"), int)
        or manifest["min_scored_per_cell"] < 1
    ):
        raise ValueError("invalid frozen calibration design")
    for probe in probes.values():
        if (
            probe["workload"] not in workloads
            or probe["difficulty"] not in difficulties
            or not probe.get("stage") or not probe.get("cluster_id")
            or not re.fullmatch(r"[0-9a-f]{64}", str(probe.get("prompt_sha256")))
            or not re.fullmatch(r"[0-9a-f]{64}", str(probe.get("validator_sha256")))
        ):
            raise ValueError(f"invalid probe design: {probe.get('probe_id')}")
    observed: dict[tuple[str, str], dict] = {}
    with ledger_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            key = (record.get("model_slot"), record.get("probe_id"))
            if key in observed or key[0] not in models or key[1] not in probes:
                raise ValueError(f"duplicate/unknown model-probe pair at line {line_number}")
            model = models[key[0]]
            probe = probes[key[1]]
            if (
                record.get("outcome") not in OUTCOMES
                or record.get("exact_model_version") != model["exact_version"]
                or record.get("prompt_sha256") != probe["prompt_sha256"]
                or record.get("validator_sha256") != probe["validator_sha256"]
            ):
                raise ValueError(f"frozen model/prompt/validator mismatch at line {line_number}")
            if record["outcome"] == "environment_invalid" and not record.get("reason"):
                raise ValueError(f"environment exclusion without reason at line {line_number}")
            observed[key] = record
    cells = []
    counts_gate_passed = True
    for slot in sorted(models):
        for workload in workloads:
            for difficulty in difficulties:
                planned = [item for item in probes.values()
                           if item["workload"] == workload and item["difficulty"] == difficulty]
                outcomes = [observed.get((slot, item["probe_id"])) for item in planned]
                counts = {name: sum(
                    record is not None and record["outcome"] == name for record in outcomes
                ) for name in OUTCOMES}
                missing = sum(record is None for record in outcomes)
                n = counts["verified"] + counts["model_failed"] + counts["provider_failed"]
                low, high = wilson(counts["verified"], n)
                enough = n >= manifest["min_scored_per_cell"] and missing == 0
                counts_gate_passed &= enough
                cells.append({
                    "model_slot": slot, "workload": workload, "difficulty": difficulty,
                    "planned_probes": len(planned), "scored_attempts": n,
                    "verified": counts["verified"],
                    "model_failed": counts["model_failed"],
                    "provider_failed": counts["provider_failed"],
                    "environment_invalid": counts["environment_invalid"],
                    "missing": missing,
                    "observed_rate": counts["verified"] / n if n else None,
                    "wilson95_low": low, "wilson95_high": high,
                    "counts_gate_passed": enough,
                    "stage_types": sorted({item["stage"] for item in planned}),
                    "source_clusters": sorted({item["cluster_id"] for item in planned}),
                })
    return {
        "status": "held_out_calibration_counts_audited",
        "data_scope": "held_out_calibration_only",
        "not_a_policy_comparison": True,
        "not_a_simulator_parameter_fit": True,
        "counts_gate_passed": counts_gate_passed,
        "requires_methods_review": True,
        "note": "Wilson intervals are descriptive; stage/corpus dependence and difficulty-label validity remain to be assessed.",
        "manifest_sha256": sha256(manifest_path),
        "ledger_sha256": sha256(ledger_path),
        "models": len(models), "probes": len(probes), "ledger_rows": len(observed),
        "cells": cells,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(summarize(args.manifest, args.ledger), indent=2) + "\n"
    if args.output:
        path = args.output.resolve()
        if not path.is_relative_to((HERE / "results").resolve()) or path.exists():
            raise ValueError("output must be a new path inside v2.3/results")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result, encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()
