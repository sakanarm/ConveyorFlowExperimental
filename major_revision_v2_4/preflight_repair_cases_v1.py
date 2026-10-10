"""Run one frozen BugsInPy environment gate in rootful Podman; never call an LLM.

The v2.3 trusted preflight engine is reused without changing its historical
source. Its workspace root is redirected to this separate v2.4 directory.
An interrupted case is never silently relaunched: inspect its retained tree.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

import select_repair_cases_v1 as selection


HERE = Path(__file__).resolve().parent
V2 = HERE.parent
PREVIOUS = V2 / "major_revision_v2_3"
ROOT = HERE / "results/preflight_v1"
CONFIG = ROOT / "config.json"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"

sys.path.insert(0, str(PREVIOUS))
import run_bugsinpy_preflight as engine  # noqa: E402


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, data: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")


def expected_config() -> dict:
    config = load(PREVIOUS / "config_bugsinpy_preflight_v2.json")
    config["max_candidates"] = 1
    config["profiles"]["luigi"]["packages"].append("nose==1.3.7")
    config["profiles"]["matplotlib"]["build"] = "python setup.py build_ext --inplace -j 1"
    config["profiles"]["fastapi"] = {
        "url": "https://github.com/fastapi/fastapi",
        "packages": [
            "pytest==5.4.3", "pydantic==0.32.2", "starlette==0.12.8",
            "requests==2.23.0", "python-multipart==0.0.5",
            "email-validator==1.1.1", "aiofiles==0.5.0",
            "Jinja2==2.11.2", "itsdangerous==1.1.0", "websockets==8.1",
        ],
        "build": "true",
    }
    config["environment_deviation"] = (
        "v2.4 new-case preflight, CPython 3.8.20 and pinned minimal dependencies; "
        "Luigi nose recovery and serial Matplotlib build carried from audited v2.3; "
        "FastAPI minimal pinned profile from public BugsInPy metadata. "
        "This is not an exact historical environment. No LLM outcomes enter selection."
    )
    return config


def expected_dependencies() -> dict[str, str]:
    return {
        "cohort": sha256(selection.OUTPUT),
        "preflight_wrapper": sha256(Path(__file__)),
        "trusted_preflight_engine": sha256(PREVIOUS / "run_bugsinpy_preflight.py"),
        "trusted_selector": sha256(PREVIOUS / "select_bugsinpy_pilot.py"),
        "container_cli": sha256(PREVIOUS / "container_cli.py"),
        "base_config": sha256(PREVIOUS / "config_bugsinpy_preflight_v2.json"),
    }


def freeze() -> dict:
    if load(selection.OUTPUT) != (planned := selection.plan()) | {
            "created_at_utc": load(selection.OUTPUT)["created_at_utc"]}:
        raise ValueError("Cohort audit mismatch")
    dependencies = expected_dependencies()
    config = expected_config()
    if LOCK.exists():
        locked = load(LOCK)
        if locked["dependencies_sha256"] != dependencies or load(CONFIG) != config:
            raise ValueError("Frozen preflight source or config drift")
        if locked["config_sha256"] != sha256(CONFIG):
            raise ValueError("Frozen config hash drift")
        return locked
    if ROOT.exists():
        raise FileExistsError("Preflight root exists without lock")
    ROOT.mkdir(parents=True)
    save_new(CONFIG, config)
    locked = {
        "status": "v2_4_environment_preflight_frozen_no_provider_calls",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dependencies_sha256": dependencies,
        "config_sha256": sha256(CONFIG),
        "candidate_queue_sha256": sha256(selection.OUTPUT),
        "provider_calls": 0,
        "paid_execution_allowed": False,
        "target_per_project": selection.TARGET_PER_PROJECT,
    }
    save_new(LOCK, locked)
    return locked


def records() -> list[dict]:
    return [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()] if LEDGER.is_file() else []


def audit() -> dict:
    lock = freeze()
    cohort = load(selection.OUTPUT)
    rows = records()
    seen = set()
    counts = {project: 0 for project in selection.PROJECTS}
    for row in rows:
        project, index = row["project"], row["queue_index"]
        queue = cohort["queues"][project]
        if (row["case_id"] != queue[index]["case_id"] or
                row["selection_hash"] != queue[index]["selection_hash"] or
                (project, index) in seen):
            raise ValueError("Preflight ledger identity/order mismatch")
        seen.add((project, index))
        if row["status"] == "reproducible":
            counts[project] += 1
        elif row["status"] != "environment_excluded":
            raise ValueError("Unexpected environment status")
        proof = ROOT / project / row["case_id"] / "engine_ledger.jsonl"
        proof_rows = [json.loads(line) for line in proof.read_text(encoding="utf-8").splitlines()
                      if line.strip()]
        if len(proof_rows) != 1 or proof_rows[0]["selection_hash"] != row["selection_hash"]:
            raise ValueError("Engine evidence missing or changed")
    for project in selection.PROJECTS:
        indexes = sorted(index for p, index in seen if p == project)
        if indexes != list(range(len(indexes))):
            raise ValueError("Project queue has a skipped preflight")
    return {"status": "preflight_audited_not_paid_ready", "lock_sha256": sha256(LOCK),
            "cohort_sha256": lock["candidate_queue_sha256"],
            "records": len(rows), "reproducible_per_project": counts,
            "provider_calls": 0, "paid_execution_allowed": False}


def run_next(project: str) -> dict:
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman only")
    frozen = audit()
    if frozen["reproducible_per_project"][project] >= selection.TARGET_PER_PROJECT:
        return {"status": "project_environment_target_met", "project": project,
                "provider_calls": 0}
    cohort = load(selection.OUTPUT)
    queue = cohort["queues"][project]
    seen = {row["queue_index"] for row in records() if row["project"] == project}
    index = len(seen)
    if index >= len(queue):
        return {"status": "project_environment_queue_exhausted", "project": project,
                "reproducible": frozen["reproducible_per_project"][project],
                "provider_calls": 0}
    case = queue[index]
    case_root = ROOT / project / case["case_id"]
    if case_root.exists():
        raise FileExistsError("Case was already started; inspect/recover, never blind rerun")
    case_root.mkdir(parents=True)
    manifest = case_root / "manifest.json"
    save_new(manifest, {"status": "metadata_only_not_preflighted", "candidates": [case]})
    engine.HERE = HERE
    engine.MANIFEST = manifest
    local_ledger = case_root / "engine_ledger.jsonl"
    prefix = f"v24_pf_{project}_{case['bug_id']}"
    print(json.dumps({"status": "environment_preflight_started", "case_id": case["case_id"],
                      "queue_index": index, "provider_calls": 0}), flush=True)
    engine.run_next(CONFIG, local_ledger, prefix)
    result = [json.loads(line) for line in local_ledger.read_text(encoding="utf-8").splitlines()
              if line.strip()]
    if len(result) != 1 or result[0]["selection_hash"] != case["selection_hash"]:
        raise ValueError("Trusted engine did not produce one matching record")
    row = {"project": project, "queue_index": index, "case_id": case["case_id"],
           "selection_hash": case["selection_hash"], "status": result[0]["status"],
           "engine_record_sha256": sha256(local_ledger), "provider_calls": 0}
    with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--audit", action="store_true")
    group.add_argument("--run-next", choices=selection.PROJECTS)
    args = parser.parse_args()
    result = (run_next(args.run_next) if args.run_next else
              audit() if args.audit else {"status": freeze()["status"],
                                      "lock_sha256": sha256(LOCK), "provider_calls": 0})
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
