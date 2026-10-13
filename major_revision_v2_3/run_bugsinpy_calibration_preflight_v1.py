"""Freeze and preflight a new, stratified, outcome-blind repository pool.

No model calls. Validator-only images contain fixed code and must never be
mounted in a candidate sandbox. The earlier feasibility engine is unchanged.
"""
import argparse
import copy
import json
import shlex
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import run_bugsinpy_preflight as engine
from select_bugsinpy_pilot import sha256

HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/bugsinpy_calibration_preflight_v1"
PROJECTS = ("luigi", "matplotlib", "pandas")
TARGET_PER_PROJECT = 2
MAX_PER_PROJECT = 4
SOURCE = HERE / "bugsinpy_candidate_manifest.json"
EXPOSED = HERE / "results/bugsinpy_serial_build_recovery_v6_protocol/combined_prefix_ledger.jsonl"


def candidates(manifest, exposed, read_command):
    old = {(r["project"], r["bug_id"]) for r in exposed}
    groups = {}
    counts = {}
    for project in PROJECTS:
        pool = []
        for item in manifest["candidates"]:
            if item["project"] != project or (project, item["bug_id"]) in old:
                continue
            if not item["python_version"].startswith("3.8."):
                continue
            command = shlex.split(read_command(item).strip())
            if len(command) != 2 or command[0] != "pytest" or not command[1].startswith(item["test_file"]):
                continue
            pool.append(item)
        pool.sort(key=lambda r: r["selection_hash"])
        if len(pool) < MAX_PER_PROJECT:
            raise ValueError("insufficient predeclared, supported pool: " + project)
        counts[project] = len(pool)
        groups[project] = pool[:MAX_PER_PROJECT]
    ordered = [groups[p][rank] for rank in range(MAX_PER_PROJECT) for p in PROJECTS]
    return ordered, counts


def write_frozen(path, value):
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise ValueError("frozen preflight input changed: " + str(path))
    else:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def freeze():
    dependencies = {name: sha256(HERE / name) for name in (
        "bugsinpy_candidate_manifest.json", "config_bugsinpy_preflight_v2.json",
        "run_bugsinpy_preflight.py", "select_bugsinpy_pilot.py", "container_cli.py",
        "run_bugsinpy_calibration_preflight_v1.py")}
    dependencies[EXPOSED.relative_to(HERE).as_posix()] = sha256(EXPOSED)
    if (ROOT / "lock.json").exists():
        lock = json.loads((ROOT / "lock.json").read_text(encoding="utf-8"))
        if lock["dependencies"] != dependencies:
            raise ValueError("calibration preflight dependency changed after freeze")
        for name in ("manifest.json", "config.json"):
            if sha256(ROOT / name) != lock["artifact_hashes"][name]:
                raise ValueError("calibration preflight frozen artifact changed")
        return lock
    manifest = json.loads(SOURCE.read_text(encoding="utf-8"))
    exposed = [json.loads(line) for line in EXPOSED.read_text(encoding="utf-8").splitlines() if line.strip()]
    ordered, counts = candidates(manifest, exposed, lambda item: (
        HERE.parent / "bip/projects" / item["project"] / "bugs" / item["bug_id"] / "run_test.sh"
    ).read_text(encoding="utf-8"))
    settings = copy.deepcopy(json.loads((HERE / "config_bugsinpy_preflight_v2.json").read_text(encoding="utf-8")))
    settings["max_candidates"] = 1
    settings["profiles"]["luigi"]["packages"].append("nose==1.3.7")
    settings["profiles"]["matplotlib"]["build"] = "python setup.py build_ext --inplace -j 1"
    settings["environment_deviation"] = (
        "New outcome-blind calibration-preparation pool, not historical-environment reproduction. "
        "Use the documented feasibility environment revisions before any new tests: common Python "
        "3.8.20, -O0 -g0, pinned minimal packages; nose 1.3.7 for every Luigi candidate; serial "
        "extension build for every Matplotlib candidate. Repository source and original metadata/tests "
        "are unchanged. No provider calls, no previous model repair or gold patch is a selection criterion."
    )
    ROOT.mkdir(parents=True)
    write_frozen(ROOT / "manifest.json", {"status": "metadata_only_not_preflighted", "candidates": ordered,
        "source_commit": manifest["source_commit"], "supported_population_counts": counts,
        "scope": "new Python 3.8, single pytest invocation in Luigi/Matplotlib/Pandas; excluded feasibility prefix",
        "rule": "Selection hash order within repository, round-robin strata; first two reproducible per stratum, at most four attempted per stratum. Record every exclusion and every deterministic quota skip before model calls.",
        "target_per_repository": TARGET_PER_PROJECT, "max_preflights_per_repository": MAX_PER_PROJECT,
        "no_llm_calls": True, "research_results": False})
    write_frozen(ROOT / "config.json", settings)
    lock = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "new_case_preflight_frozen_before_execution",
        "dependencies": dependencies, "artifact_hashes": {n: sha256(ROOT / n) for n in ("manifest.json", "config.json")},
        "max_preflights": len(ordered), "target_cases": len(PROJECTS) * TARGET_PER_PROJECT,
        "no_llm_calls": True, "not_yet_calibration_results": True}
    write_frozen(ROOT / "lock.json", lock)
    return lock


def run():
    lock = freeze()
    pool = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))["candidates"]
    ledger = ROOT / "ledger.jsonl"
    records = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()] if ledger.exists() else []
    if len(records) > len(pool):
        raise ValueError("too many calibration preflight records")
    for index, row in enumerate(records):
        if any(row[k] != pool[index][k] for k in ("project", "bug_id", "selection_hash")):
            raise ValueError("calibration ledger skipped or reordered a candidate")
    ready = Counter(r["project"] for r in records if r["status"] == "reproducible")
    for index in range(len(records), len(pool)):
        item = pool[index]
        case_id = item["project"] + "_" + item["bug_id"]
        if ready[item["project"]] >= TARGET_PER_PROJECT:
            record = {k: item[k] for k in ("project", "bug_id", "selection_hash")}
            record.update(status="not_requested_stratum_quota_met", no_llm_calls=True)
        else:
            directory = ROOT / case_id
            directory.mkdir(exist_ok=True)
            subset = directory / "manifest.json"
            write_frozen(subset, {"status": "metadata_only_not_preflighted", "candidates": [item]})
            local_ledger = directory / "engine_ledger.jsonl"
            print(json.dumps({"status": "new_case_preflight_started", "index": index, "case_id": case_id, "llm_calls": 0}), flush=True)
            previous_manifest = engine.MANIFEST
            engine.MANIFEST = subset
            try:
                if not local_ledger.exists():
                    engine.run_next(ROOT / "config.json", local_ledger, "calibration_preflight_v1_" + str(index).zfill(2))
            finally:
                engine.MANIFEST = previous_manifest
            entries = [json.loads(line) for line in local_ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
            if len(entries) != 1 or entries[0]["selection_hash"] != item["selection_hash"]:
                raise ValueError("unexpected single-case engine ledger")
            record = entries[0]
            if record["config_sha256"] != lock["artifact_hashes"]["config.json"]:
                raise ValueError("case used another environment config")
            if record["status"] == "reproducible":
                ready[item["project"]] += 1
        record.update(pool_index=index, calibration_preflight_lock_sha256=sha256(ROOT / "lock.json"))
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        records.append(record)
        print(json.dumps({"case_id": case_id, "status": record["status"], "ready_per_repository": dict(ready), "llm_calls": 0}), flush=True)
    selected = [r for r in records if r["status"] == "reproducible"]
    summary = {"status": "new_case_preflight_ready" if all(ready[p] == TARGET_PER_PROJECT for p in PROJECTS) else "new_case_preflight_insufficient",
        "selected": [{k: r[k] for k in ("project", "bug_id", "selection_hash", "artifact_directory", "container_image_id")} for r in selected],
        "ready_per_repository": dict(ready), "record_statuses": dict(Counter(r["status"] for r in records)),
        "lock_sha256": sha256(ROOT / "lock.json"), "ledger_sha256": sha256(ledger), "llm_calls": 0,
        "not_yet_calibration_results": True, "research_results": False}
    write_frozen(ROOT / "summary.json", summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        print(json.dumps(freeze(), indent=2))
    elif args.execute:
        run()
    else:
        parser.error("freeze or execute explicitly")
