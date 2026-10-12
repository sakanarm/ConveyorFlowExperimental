"""Freeze the next v2.6 Scrapy source queue and every public test command.

This is metadata preparation, not a runnable environment or LLM result.
Commands are copied from BugsInPy and must all be executed per case at the
later public-contrast gate; no post-outcome selection is permitted.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shlex

from build_prior_exposure_ledger_v1 import HERE, MANIFEST
from build_unexposed_candidate_queue_v1 import OUTPUT as SOURCE_QUEUE

ROOT = HERE / "scrapy_source_queue_v1"
QUEUE = ROOT / "queue.json"
LOCK = ROOT / "lock.json"
PROJECT = "scrapy"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path: Path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def plans():
    source = read(SOURCE_QUEUE)
    if source["status"] != "metadata_queue_not_preflighted_not_main_cohort":
        raise ValueError("Upstream source queue status drift")
    frame = next(row for row in source["projects"] if row["project"] == PROJECT)
    ordered = [row for row in frame["cases_in_frozen_hash_order"]
               if not row["prior_provider_exposure"]]
    manifest = {f"{row['project']}_{row['bug_id']}": row
                for row in read(MANIFEST)["candidates"]}
    queue = []
    for order, item in enumerate(ordered):
        case = manifest[item["case_id"]]
        bug_id = str(case["bug_id"])
        metadata = HERE.parent / "bip/projects/scrapy/bugs" / bug_id
        test_files = [PurePosixPath(path.strip()) for path in case["test_file"].split(";")]
        if (not test_files or len(set(test_files)) != len(test_files) or
                any(path.is_absolute() or ".." in path.parts or
                    path.suffix != ".py" for path in test_files)):
            raise ValueError(f"Unsafe public test file: {item['case_id']}")
        lines = [line.strip() for line in (metadata / "run_test.sh").read_text(
            encoding="utf-8").splitlines() if line.strip()]
        if not lines or len(set(lines)) != len(lines):
            raise ValueError(f"Empty or duplicate commands: {item['case_id']}")
        modules = [str(path)[:-3].replace("/", ".") for path in test_files]
        commands = []
        for line in lines:
            argv = shlex.split(line)
            if (len(argv) != 5 or argv[:4] != ["python", "-m", "unittest", "-q"]
                    or not any(argv[4].startswith(module + ".")
                               for module in modules)
                    or any(symbol in argv[4] for symbol in (";", "`", "\n", "\r"))):
                raise ValueError(f"Unsupported public command: {item['case_id']}")
            commands.append(argv)
        queue.append({"queue_index": order, "case_id": item["case_id"],
                      "bug_id": bug_id, "selection_hash": item["case_order_sha256"],
                      "bug_info_sha256": sha(metadata / "bug.info"),
                      "requirements_sha256": sha(metadata / "requirements.txt"),
                      "run_test_sha256": sha(metadata / "run_test.sh"),
                      "test_files": [str(path) for path in test_files],
                      "public_commands": commands,
                      "buggy_commit_id": case["buggy_commit_id"],
                      "fixed_commit_id_validator_only":
                          case["fixed_commit_id_for_validator_only"]})
    if len(queue) != frame["unexposed_candidate_count"] or len(queue) < 2:
        raise ValueError("Scrapy queue length drift")
    return queue


def freeze():
    queue = plans()
    stable = {"status": "scrapy_metadata_frozen_not_preflighted",
              "source_queue_sha256": sha(SOURCE_QUEUE),
              "manifest_sha256": sha(MANIFEST),
              "runner_sha256": sha(Path(__file__)),
              "selection_rule": "Frozen project/case hash order; retain all exclusions; first two fully qualified cases only",
              "public_test_rule": "Execute every declared unittest command on both buggy and fixed validators",
              "cases": len(queue), "provider_calls": 0,
              "paid_execution_allowed": False}
    if LOCK.exists():
        old = read(LOCK)
        if (any(old.get(key) != value for key, value in stable.items()) or
                read(QUEUE) != queue or old["queue_sha256"] != sha(QUEUE)):
            raise ValueError("Existing Scrapy source freeze drift")
        return old
    if ROOT.exists():
        raise FileExistsError("Partial Scrapy source queue root")
    ROOT.mkdir()
    save_new(QUEUE, queue)
    lock = {**stable, "queue_sha256": sha(QUEUE),
            "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, lock)
    return lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args()
    if not args.freeze:
        parser.error("--freeze required")
    lock = freeze()
    print(json.dumps({"status": lock["status"], "cases": lock["cases"],
                      "provider_calls": 0, "lock_sha256": sha(LOCK)},
                     sort_keys=True))


if __name__ == "__main__":
    main()
