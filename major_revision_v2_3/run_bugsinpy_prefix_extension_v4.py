"""Continue one unsupported-profile candidate without skipping its index."""
import copy
import hashlib
import json
from pathlib import Path
import run_bugsinpy_preflight as engine
from select_bugsinpy_pilot import MANIFEST, select

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config_bugsinpy_prefix_extension_v4.json"
ROOT = HERE / "results" / "bugsinpy_prefix_extension_v4"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_write(path, content):
    if path.exists():
        assert json.loads(path.read_text(encoding="utf-8")) == content, "Frozen input changed"
    else:
        path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")


def main():
    settings = json.loads(CONFIG.read_text(encoding="utf-8"))
    previous_path = HERE / settings["source_ledger"]
    previous = [json.loads(line) for line in previous_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    state = select(MANIFEST, previous_path)
    assert not state["selected"]
    index = settings["candidate_index"]
    assert len(previous) == settings["expected_prefix_length"] == index
    candidate = json.loads(MANIFEST.read_text(encoding="utf-8"))["candidates"][index]
    assert candidate["project"] == "thefuck" and candidate["bug_id"] == "32"
    ROOT.mkdir(exist_ok=True)
    lock = {"config_sha256": digest(CONFIG), "source_ledger_sha256": digest(previous_path),
            "source_manifest_sha256": digest(MANIFEST), "runner_sha256": digest(Path(__file__)),
            "preflight_engine_sha256": digest(Path(engine.__file__)), "llm_calls": 0}
    frozen_write(ROOT / "lock.json", lock)
    cfg_path, subset_path = ROOT / "config.json", ROOT / "manifest.json"
    frozen_write(cfg_path, settings["preflight_config"])
    frozen_write(subset_path, {"status": "metadata_only_not_preflighted", "candidates": [candidate]})
    ledger = ROOT / "new_case_ledger.jsonl"
    if not ledger.exists():
        print(json.dumps({"status": "next_frozen_candidate_started", "index": index,
                          "project": candidate["project"], "bug_id": candidate["bug_id"], "llm_calls": 0}), flush=True)
        original_manifest = engine.MANIFEST
        engine.MANIFEST = subset_path
        try:
            engine.run_next(cfg_path, ledger, "bugsinpy_prefix_extension_v4_006")
        finally:
            engine.MANIFEST = original_manifest
    records = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(records) == 1
    record = copy.deepcopy(records[0])
    assert record["selection_hash"] == candidate["selection_hash"]
    assert record["config_sha256"] == digest(cfg_path)
    record["original_manifest_index"] = index
    record["source_prefix_ledger_sha256"] = lock["source_ledger_sha256"]
    combined = ROOT / "combined_prefix_ledger.jsonl"
    content = "".join(json.dumps(item, sort_keys=True) + "\n" for item in previous + [record])
    if combined.exists():
        assert combined.read_text(encoding="utf-8") == content
    else:
        combined.write_text(content, encoding="utf-8")
    selected = select(MANIFEST, combined)
    frozen_write(ROOT / "selection.json", selected)
    print(json.dumps(selected, indent=2), flush=True)


if __name__ == "__main__":
    main()
