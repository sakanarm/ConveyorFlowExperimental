"""Recover environment exclusions without rewriting v2 evidence or LLM calls.

The unchanged v2 runner is used through a short, explicit candidate view. Its
original metadata manifest and records are preserved; output records reference
the corresponding original selection index, configuration and source evidence.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import run_bugsinpy_preflight as engine
from select_bugsinpy_pilot import MANIFEST, select

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config_bugsinpy_environment_recovery_v3.json"
ROOT = HERE / "results" / "bugsinpy_environment_recovery_v3"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    policy = json.loads(CONFIG.read_text(encoding="utf-8"))
    base_path = HERE / policy["source_config"]
    source_ledger = HERE / policy["source_ledger"]
    settings = json.loads(base_path.read_text(encoding="utf-8"))
    candidates = json.loads(MANIFEST.read_text(encoding="utf-8"))["candidates"]
    old = [json.loads(line) for line in source_ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(old) == 6, "Recovery is scoped to the completed six-case prefix"
    select(MANIFEST, source_ledger)  # checks order and required evidence
    ROOT.mkdir(exist_ok=True)
    lock_path = ROOT / "recovery_lock.json"
    lock = {"config_sha256": digest(CONFIG), "source_config_sha256": digest(base_path),
            "source_ledger_sha256": digest(source_ledger), "source_manifest_sha256": digest(MANIFEST),
            "recovery_runner_sha256": digest(Path(__file__)),
            "unchanged_preflight_runner_sha256": digest(Path(engine.__file__)),
            "llm_calls": 0}
    if lock_path.exists():
        assert json.loads(lock_path.read_text(encoding="utf-8")) == lock, "Frozen recovery inputs changed"
    else:
        lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    recovered = {}
    for index in policy["recovery_indices"]:
        item = candidates[index]
        assert old[index]["status"] == "environment_excluded"
        assert all(old[index][key] == item[key] for key in ("project", "bug_id", "selection_hash"))
        label = f"bugsinpy_environment_recovery_v3_{index:03d}"
        cfg = copy.deepcopy(settings)
        override = policy["profile_overrides"][item["project"]]
        cfg["max_candidates"] = 1
        if "compile_flags" in override:
            cfg["compile_flags"] = override["compile_flags"]
        cfg["profiles"][item["project"]]["packages"] += override.get("additional_packages", [])
        cfg["environment_deviation"] += " Recovery v3: " + override["reason"]
        config_path = ROOT / f"config_{index:03d}.json"
        manifest_path = ROOT / f"manifest_{index:03d}.json"
        ledger_path = ROOT / f"ledger_{index:03d}.jsonl"
        subset = {"status": "metadata_only_not_preflighted", "candidates": [item]}
        for path, content in ((config_path, cfg), (manifest_path, subset)):
            if path.exists():
                assert json.loads(path.read_text(encoding="utf-8")) == content
            else:
                path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
        # No skipping: the one-candidate view contains exactly the original
        # metadata item. run_next still verifies its original metadata hashes.
        records = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()] if ledger_path.exists() else []
        assert len(records) <= 1
        if not records:
            print(json.dumps({"status": "environment_recovery_started", "original_index": index,
                              "project": item["project"], "bug_id": item["bug_id"], "llm_calls": 0}), flush=True)
            original_manifest = engine.MANIFEST
            engine.MANIFEST = manifest_path
            try:
                result = engine.run_next(config_path, ledger_path, label)
            finally:
                engine.MANIFEST = original_manifest
            record = result["record"]
        else:
            record = records[0]
        assert all(record[key] == item[key] for key in ("project", "bug_id", "selection_hash"))
        assert record["config_sha256"] == digest(config_path)
        recovered[index] = record
        print(json.dumps({"status": "environment_recovery_recorded", "original_index": index,
                          "outcome": record["status"], "project": item["project"]}), flush=True)
    combined = ROOT / "combined_prefix_ledger.jsonl"
    evidence = []
    for index, previous in enumerate(old):
        record = copy.deepcopy(recovered.get(index, previous))
        record["recovery_v3_original_index"] = index
        record["prior_record_sha256"] = hashlib.sha256(json.dumps(previous, sort_keys=True).encode()).hexdigest()
        record["carried_unchanged_not_reexecuted"] = index not in recovered
        record["source_ledger_sha256"] = lock["source_ledger_sha256"]
        evidence.append(record)
    content = "".join(json.dumps(record, sort_keys=True) + "\n" for record in evidence)
    if combined.exists():
        assert combined.read_text(encoding="utf-8") == content
    else:
        combined.write_text(content, encoding="utf-8")
    selection = select(MANIFEST, combined)
    out = ROOT / "selection.json"
    if out.exists():
        assert json.loads(out.read_text(encoding="utf-8")) == selection
    else:
        out.write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(selection, indent=2), flush=True)


if __name__ == "__main__":
    main()
