"""Pre-provider Cookiecutter source eligibility in the frozen v2.6 order.

The public BugsInPy commands use `tox <pytest-node>` rather than a native
pytest command. For a one-line command we run the exact node directly under
pinned pytest in Python 3.6.15. This is a disclosed harness normalization,
not a change to the bug or test. Multiline commands require a new amendment.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import sys

from build_prior_exposure_ledger_v1 import HERE, MANIFEST
from build_unexposed_candidate_queue_v1 import OUTPUT as SOURCE_QUEUE

V2 = HERE.parent
ENGINE_DIR = V2 / "major_revision_v2_5"
sys.path.insert(0, str(V2 / "major_revision_v2_3"))
sys.path.insert(0, str(ENGINE_DIR))
import preflight_oci_v2 as engine  # noqa: E402

PROJECT = "cookiecutter"
ROOT = HERE / "cookiecutter_preflight_v1"
QUEUE, CONFIG, LOCK, LEDGER = (ROOT / name for name in
                               ("queue.json", "config.json", "lock.json", "ledger.jsonl"))
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/cookiecutter_preflight_v1"
RAW = Path(RAW_TEXT if os.name != "nt" else "D:/ConveyorFlowRuntime/v2_6/cookiecutter_preflight_v1")
BASE = "docker.io/library/python:3.6.15-slim-buster@sha256:e10aa83604948c6d8d9f72a9a20193d84bb2dbe550b725eb5208387117fde065"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path: Path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def normalized_test(case: dict, script: Path) -> str:
    lines = [line.strip() for line in script.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    if len(lines) != 1:
        raise ValueError("Multiline public tox command requires separate amendment")
    args = shlex.split(lines[0])
    node = args[1] if len(args) == 2 and args[0] == "tox" else ""
    expected = PurePosixPath(case["test_file"])
    if (expected.is_absolute() or ".." in expected.parts or
            not node.startswith(str(expected) + "::") or
            any(c in node for c in (";", "`", "\n", "\r"))):
        raise ValueError("Unsupported or unsafe public tox selector")
    return node


def plans():
    source = read(SOURCE_QUEUE)
    if source["status"] != "metadata_queue_not_preflighted_not_main_cohort":
        raise ValueError("Source queue status drift")
    frame = next(row for row in source["projects"] if row["project"] == PROJECT)
    ordered = [row for row in frame["cases_in_frozen_hash_order"]
               if not row["prior_provider_exposure"]]
    manifest = {f"{row['project']}_{row['bug_id']}": row for row in read(MANIFEST)["candidates"]}
    queue = []
    for row in ordered:
        case = dict(manifest[row["case_id"]])
        case["selection_hash"] = row["case_order_sha256"]
        queue.append(case)
    if [f"{PROJECT}_{row['bug_id']}" for row in queue] != [row["case_id"] for row in ordered] or len(queue) != 4:
        raise ValueError("Cookiecutter queue mismatch")
    config = {
        "status": "v2_6_cookiecutter_public_source_preflight_only",
        "base_image": BASE,
        "python_scope": "3.6",
        "common_packages": ["pip==21.3.1", "setuptools==59.6.0", "wheel==0.37.1"],
        "compile_flags": "-O0 -g0",
        "max_candidates": 4,
        "build_timeout_seconds": 1800,
        "test_timeout_seconds": 180,
        "environment_deviation": (
            "Cookiecutter public metadata specifies Python 3.6.9 and tox. "
            "This preflight uses pinned official Python 3.6.15, directly runs "
            "the metadata's one-line pytest node under pytest 5.4.3, and "
            "omits the invalid pkg-resources==0.0.0 editable-requirement entry. "
            "It is not an exact historical tox environment. No LLM outcome "
            "informed this profile."
        ),
        "profiles": {PROJECT: {
            "url": "https://github.com/cookiecutter/cookiecutter.git",
            "build": "python setup.py develop",
            "packages": [
                "pytest==5.4.3", "tox==3.15.2", "arrow==0.15.6",
                "binaryornot==0.4.4", "click==7.1.2", "Jinja2==2.11.2",
                "jinja2-time==0.2.0", "MarkupSafe==1.1.1", "poyo==0.5.0",
                "python-slugify==4.0.0", "requests==2.23.0",
            ],
        }},
    }
    return queue, config


def freeze():
    queue, config = plans()
    expected = {
        "status": "v2_6_cookiecutter_preflight_frozen_before_provider",
        "source_queue_sha256": sha(SOURCE_QUEUE),
        "manifest_sha256": sha(MANIFEST),
        "runner_sha256": sha(Path(__file__)),
        "engine_sha256": sha(ENGINE_DIR / "preflight_oci_v2.py"),
        "selection_rule": "First two reproducible cases in frozen order; retain every exclusion",
        "raw_root": RAW_TEXT,
        "provider_calls": 0,
        "paid_execution_allowed": False,
    }
    if LOCK.exists():
        old = read(LOCK)
        if (any(old.get(key) != value for key, value in expected.items()) or
                read(QUEUE) != queue or read(CONFIG) != config or
                old["queue_sha256"] != sha(QUEUE) or old["config_sha256"] != sha(CONFIG)):
            raise ValueError("Cookiecutter preflight lock drift")
        return old
    if ROOT.exists():
        raise FileExistsError("Partial Cookiecutter preflight root")
    ROOT.mkdir()
    save_new(QUEUE, queue)
    save_new(CONFIG, config)
    lock = {**expected, "queue_sha256": sha(QUEUE), "config_sha256": sha(CONFIG),
            "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, lock)
    return lock


def audit():
    freeze()
    rows = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()] if LEDGER.exists() else []
    queue = read(QUEUE)
    if len(rows) > len(queue):
        raise ValueError("Too many Cookiecutter attempts")
    for index, row in enumerate(rows):
        case = queue[index]
        record = RAW / f"{index:02d}_{PROJECT}_{case['bug_id']}/preflight_record.json"
        if (row["queue_index"] != index or row["case_id"] != f"{PROJECT}_{case['bug_id']}" or
                row["selection_hash"] != case["selection_hash"] or
                row["record_sha256"] != sha(record)):
            raise ValueError("Cookiecutter ledger/evidence drift")
    good = [row["case_id"] for row in rows if row["status"] == "reproducible"]
    return {"status": "two_public_contrasts" if len(good) == 2 else
            "project_ineligible" if len(rows) == len(queue) else "preflight_incomplete",
            "attempted": len(rows), "qualified_cases": good,
            "provider_calls": 0, "lock_sha256": sha(LOCK)}


def run_next():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    state = audit()
    if state["status"] != "preflight_incomplete":
        return state
    index = state["attempted"]
    case = read(QUEUE)[index]
    out = RAW / f"{index:02d}_{PROJECT}_{case['bug_id']}"
    out.parent.mkdir(parents=True, exist_ok=True)
    engine.normalized_test = normalized_test
    print(json.dumps({"status": "preflight_started", "case_id":
                      f"{PROJECT}_{case['bug_id']}", "provider_calls": 0}), flush=True)
    record = engine.run_one(case, read(CONFIG), out)
    row = {"queue_index": index, "case_id": f"{PROJECT}_{case['bug_id']}",
           "selection_hash": case["selection_hash"], "status": record["status"],
           "reason": record.get("reason"), "record_sha256": sha(out / "preflight_record.json"),
           "provider_calls": 0}
    with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--audit", action="store_true")
    modes.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    result = run_next() if args.run_next else audit() if args.audit else {
        "status": freeze()["status"], "lock_sha256": sha(LOCK), "provider_calls": 0}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
