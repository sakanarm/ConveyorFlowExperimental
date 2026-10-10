"""Independent read-only audit and optional seal of all amended contexts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import prepare_repair_contexts_v1b as contexts

OUTPUT = contexts.HERE / "results/repair_contexts_v1b_audit.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing nonsymlink artifact: " + str(path))
    return digest(path.read_bytes())


def audit() -> dict:
    lock = contexts.read(contexts.LOCK)
    before = contexts.read(contexts.previous.LOCK)
    if (lock["status"] != "v2_4_gold_free_contexts_v1b_frozen_no_provider_calls" or
            lock["provider_calls"] != 0 or lock["paid_execution_allowed"] is not False or
            lock["dependencies_sha256"]["predecessor_context_lock"] !=
            file_hash(contexts.previous.LOCK) or
            lock["dependencies_sha256"]["context_amendment_runner"] !=
            file_hash(contexts.HERE / "prepare_repair_contexts_v1b.py") or
            len(lock["cases"]) != 12):
        raise ValueError("Pre-provider amendment lock not intact")
    expected_symbols = {key: list(value) for key, value in before["symbols"].items()}
    expected_symbols.update(contexts.SYMBOL_OVERRIDES)
    if (lock["symbols"] != expected_symbols or
            lock["settings"]["source_excerpts_character_cap"] != 160000):
        raise ValueError("Context amendment scope/cap changed")
    rows = {}
    for case in lock["cases"]:
        cid = case["case_id"]
        folder = contexts.ROOT / cid
        summary = contexts.read(folder / "summary.json")
        prompt = contexts.read(folder / "prompt_context.json")
        full = contexts.read(folder / "full_buggy_context.json")
        baseline_path = contexts.previous.builder.ROOT / cid / "summary.json"
        baseline = contexts.read(baseline_path)
        source = full["allowed_source_files"]
        excerpt = prompt["buggy_source_excerpts"]
        count = sum(len(chunk["text"]) for chunks in excerpt.values()
                    for chunk in chunks)
        if (summary["status"] != "context_identity_passed" or
                summary["source_mutation_import_confirmed"] is not True or
                summary["no_op_patch_not_a_repair"] is not True or
                summary["trusted_mutation_not_a_repair"] is not True or
                summary["lock_sha256"] != file_hash(contexts.LOCK) or
                summary["candidate_summary_sha256"] != file_hash(baseline_path) or
                summary["full_context_sha256"] != file_hash(folder / "full_buggy_context.json") or
                summary["prompt_context_sha256"] != file_hash(folder / "prompt_context.json") or
                prompt["allowed_paths"] != case["allowed_files"] or
                set(source) != set(case["allowed_files"]) or
                set(excerpt) != set(source) or
                "allowed_source_files" in prompt or
                count != prompt["source_excerpts_characters"] or
                count != summary["source_excerpts_characters"] or
                count > 160000 or
                any(digest(text.encode("utf-8")) != baseline["candidate_audit"][
                    "allowed_source_sha256"][path] for path, text in source.items())):
            raise ValueError("Context/source/identity evidence mismatch: " + cid)
        rows[cid] = {"prompt_sha256": file_hash(folder / "prompt_context.json"),
                     "summary_sha256": file_hash(folder / "summary.json"),
                     "excerpt_characters": count}
    return {"status": "all_amended_contexts_independently_audited",
            "provider_calls": 0, "cases": 12,
            "context_lock_sha256": file_hash(contexts.LOCK),
            "predecessor_lock_sha256": file_hash(contexts.previous.LOCK),
            "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.seal:
        if OUTPUT.exists():
            if contexts.read(OUTPUT) != result:
                raise ValueError("Sealed context audit drift")
        else:
            contexts.save_new(OUTPUT, result)
    print(json.dumps({"status": result["status"], "cases": 12,
                      "provider_calls": 0, "sealed": OUTPUT.is_file()}))


if __name__ == "__main__":
    main()
