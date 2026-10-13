"""Frozen public-source preflight for multi-node FastAPI BugsInPy cases.

The BugsInPy ``test_file`` field may contain semicolon-separated paths and
``run_test.sh`` may contain several pytest commands. Every listed command is
validated and executed; no node is selected after observing its outcome.
This is source eligibility only, with zero LLM calls.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys

from build_prior_exposure_ledger_v1 import HERE, MANIFEST
from build_unexposed_candidate_queue_v1 import OUTPUT as SOURCE_QUEUE

V2 = HERE.parent
sys.path.insert(0, str(V2 / "major_revision_v2_3"))
sys.path.insert(0, str(V2 / "major_revision_v2_5"))
from container_cli import canonical_image_id, executable, runtime_version  # noqa: E402
from run_bugsinpy_preflight import environment, execute, test_counts  # noqa: E402

PROJECT = "fastapi"
ROOT = HERE / "fastapi_preflight_multinode_v1"
QUEUE, CONFIG, LOCK, LEDGER = (ROOT / name for name in
                               ("queue.json", "config.json", "lock.json", "ledger.jsonl"))
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/fastapi_preflight_multinode_v1"
RAW = Path(RAW_TEXT if os.name != "nt" else
           "D:/ConveyorFlowRuntime/v2_6/fastapi_preflight_multinode_v1")
BASE = "python:3.8.20-slim-bookworm@sha256:1d52838af602b4b5a831beb13a0e4d073280665ea7be7f69ce2382f29c5a613f"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def metadata(case):
    return V2 / "bip" / "projects" / PROJECT / "bugs" / str(case["bug_id"])


def nodes_from_public_metadata(case):
    files = [item.strip() for item in case["test_file"].split(";")]
    if not files or len(set(files)) != len(files):
        raise ValueError("Empty or duplicate test files")
    for file_name in files:
        path = PurePosixPath(file_name)
        if path.is_absolute() or ".." in path.parts or path.suffix != ".py":
            raise ValueError("Unsafe test file")
    commands = [line.strip() for line in (metadata(case) / "run_test.sh").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    if not commands:
        raise ValueError("Missing public test commands")
    nodes = []
    for command in commands:
        parts = shlex.split(command)
        if len(parts) != 2 or parts[0] != "pytest":
            raise ValueError("Unsupported public FastAPI test command")
        node = parts[1]
        if (not any(node.startswith(file_name + "::") for file_name in files) or
                any(character in node for character in (";", "`", "\n", "\r")) or
                node in nodes):
            raise ValueError("Unsafe, duplicate, or mismatched test selector")
        nodes.append(node)
    # Some public metadata lists additional files without a corresponding
    # run_test.sh command. Execute every declared command; never invent tests.
    return files, nodes


def plans():
    source = read(SOURCE_QUEUE)
    if source["status"] != "metadata_queue_not_preflighted_not_main_cohort":
        raise ValueError("Source queue drift")
    frame = next(item for item in source["projects"] if item["project"] == PROJECT)
    order = [item for item in frame["cases_in_frozen_hash_order"]
             if not item["prior_provider_exposure"]]
    manifest = {f"{item['project']}_{item['bug_id']}": item
                for item in read(MANIFEST)["candidates"]}
    queue = []
    for item in order:
        case = dict(manifest[item["case_id"]])
        case["selection_hash"] = item["case_order_sha256"]
        nodes_from_public_metadata(case)
        queue.append(case)
    if len(queue) != len(order) or len(queue) < 2:
        raise ValueError("FastAPI frozen queue mismatch")
    config = {
        "status": "v2_6_fastapi_public_source_preflight_only",
        "base_image": BASE, "python_scope": "3.8",
        "source_url": "https://github.com/tiangolo/fastapi.git",
        "selection_rule": "First two reproducible cases in frozen hash order; retain every exclusion",
        "public_test_rule": "Run every distinct pytest node from run_test.sh; each node must belong to a declared test_file path",
        "dependency_rule": (
            "Install every pinned public requirements.txt line except fastapi itself; "
            "install the buggy checkout editable without dependencies. The fixed checkout "
            "is validator-only and is not installed as the active package."),
        "environment_deviation": (
            "Public metadata specifies Python 3.8.3; pinned official Python 3.8.20 "
            "is used. All public test nodes are run separately in the same image. "
            "No LLM outcome informed the environment."),
        "build_timeout_seconds": 1800,
        "per_node_timeout_seconds": 180,
        "provider_calls": 0, "paid_execution_allowed": False,
    }
    return queue, config


def freeze():
    queue, config = plans()
    stable = {
        "status": "v2_6_fastapi_multinode_preflight_frozen_before_provider",
        "source_queue_sha256": sha(SOURCE_QUEUE),
        "manifest_sha256": sha(MANIFEST),
        "runner_sha256": sha(Path(__file__)),
        "queue_count": len(queue),
        "selection_rule": config["selection_rule"],
        "provider_calls": 0, "paid_execution_allowed": False,
        "raw_root": RAW_TEXT,
    }
    if LOCK.exists():
        old = read(LOCK)
        if (any(old.get(key) != value for key, value in stable.items()) or
                read(QUEUE) != queue or read(CONFIG) != config or
                old["queue_sha256"] != sha(QUEUE) or
                old["config_sha256"] != sha(CONFIG)):
            raise ValueError("FastAPI preflight lock drift")
        return old
    if ROOT.exists():
        raise FileExistsError("Partial FastAPI preflight root")
    ROOT.mkdir()
    save_new(QUEUE, queue)
    save_new(CONFIG, config)
    lock = {**stable, "queue_sha256": sha(QUEUE), "config_sha256": sha(CONFIG),
            "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, lock)
    return lock


def audit():
    freeze()
    rows = [json.loads(line) for line in LEDGER.read_text(
        encoding="utf-8").splitlines() if line.strip()] if LEDGER.exists() else []
    queue = read(QUEUE)
    if len(rows) > len(queue):
        raise ValueError("Too many FastAPI attempts")
    for index, row in enumerate(rows):
        case = queue[index]
        record = RAW / f"{index:02d}_{PROJECT}_{case['bug_id']}/preflight_record.json"
        if (row["queue_index"] != index or
                row["case_id"] != f"{PROJECT}_{case['bug_id']}" or
                row["selection_hash"] != case["selection_hash"] or
                row["record_sha256"] != sha(record) or row["provider_calls"] != 0):
            raise ValueError("FastAPI ledger/evidence drift")
    good = [row["case_id"] for row in rows if row["status"] == "reproducible"]
    return {"status": "two_public_contrasts" if len(good) == 2 else
            "project_ineligible" if len(rows) == len(queue) else "preflight_incomplete",
            "attempted": len(rows), "qualified_cases": good,
            "provider_calls": 0, "lock_sha256": sha(LOCK)}


def run_one(index, case, config):
    original = metadata(case)
    if (sha(original / "bug.info") != case["bug_info_sha256"] or
            sha(original / "run_test.sh") != case["run_test_sha256"]):
        raise ValueError("FastAPI public metadata drift")
    files, nodes = nodes_from_public_metadata(case)
    if not case["python_version"].startswith(config["python_scope"] + "."):
        raise ValueError("Python version outside frozen scope")
    buggy, fixed = case["buggy_commit_id"], case["fixed_commit_id_for_validator_only"]
    if not re.fullmatch(r"[0-9a-f]{40}", buggy) or not re.fullmatch(r"[0-9a-f]{40}", fixed):
        raise ValueError("Invalid frozen commits")
    out = RAW / f"{index:02d}_{PROJECT}_{case['bug_id']}"
    if out.exists():
        raise FileExistsError("Prior attempt retained; audit before retry")
    out.mkdir(parents=True)
    lines = (original / "requirements.txt").read_text(encoding="utf-8").splitlines()
    filtered = [line for line in lines if line.strip() and
                not line.lower().startswith("fastapi==")]
    if len(lines) - len(filtered) != 1:
        raise ValueError("Expected exactly one fastapi requirements line")
    (out / "requirements_filtered.txt").write_text(
        "\n".join(filtered) + "\n", encoding="utf-8")
    show_tests = " && ".join(
        f"git -C /source show {fixed}:{shlex.quote(file_name)} > "
        f"/buggy/{shlex.quote(file_name)}" for file_name in files)
    dockerfile = (
        f"FROM {config['base_image']}\n"
        "RUN apt-get update && apt-get install -y --no-install-recommends "
        "git build-essential libffi-dev && rm -rf /var/lib/apt/lists/*\n"
        "COPY requirements_filtered.txt /tmp/requirements_filtered.txt\n"
        "RUN pip install --no-cache-dir -r /tmp/requirements_filtered.txt\n"
        f"RUN git clone --filter=blob:none --no-checkout {config['source_url']} /source && "
        f"git -C /source worktree add --detach /buggy {buggy} && "
        f"git -C /source worktree add --detach /fixed {fixed}\n"
        f"RUN {show_tests}\n"
        "RUN pip install --no-cache-dir --no-deps -e /buggy\n"
        "ENV PYTHONDONTWRITEBYTECODE=1\nUSER 65534:65534\nWORKDIR /tmp\n"
    )
    (out / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    tag = f"conveyorflow-v26-fastapi-{case['bug_id']}-preflight:v1"
    built = execute([executable(), "build", "-t", tag, str(out)],
                    timeout=config["build_timeout_seconds"],
                    log=out / "build_report.json")
    record = {
        "project": PROJECT, "bug_id": str(case["bug_id"]),
        "selection_hash": case["selection_hash"],
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "runner_sha256": sha(Path(__file__)),
        "dockerfile_sha256": sha(out / "Dockerfile"),
        "filtered_requirements_sha256": sha(out / "requirements_filtered.txt"),
        "original_requirements_sha256": sha(original / "requirements.txt"),
        "build_report_sha256": sha(out / "build_report.json"),
        "public_test_files": files, "public_test_nodes": nodes,
        "environment_deviation": config["environment_deviation"],
        "container_runtime": executable(),
        "runtime_version": runtime_version(environment()),
        "provider_calls": 0, "validator_only_image": True,
    }
    if built["return_code"] != 0 or built.get("timeout"):
        record.update(status="environment_excluded", reason="container build failed or timed out")
    else:
        inspected = subprocess.run(
            [executable(), "image", "inspect", tag, "--format", "{{.Id}}"],
            capture_output=True, text=True, timeout=30, check=True, env=environment())
        image = canonical_image_id(inspected.stdout)
        outcomes = {}
        for variant in ("buggy", "fixed"):
            variant_outcomes = []
            for node_index, node in enumerate(nodes):
                reports = out / variant / f"node_{node_index:02d}"
                reports.mkdir(parents=True)
                script = (f"cp -a /{variant} /tmp/work && cd /tmp/work && "
                          "PYTHONPATH=/tmp/work python -m pytest -q " +
                          shlex.quote(node) + " --junitxml=/reports/tests.xml")
                executed = execute([
                    executable(), "run", "--rm", "--network", "none", "--read-only",
                    "--cpus", "2", "--memory", "4g", "--pids-limit", "256",
                    "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                    "--user", "65534:65534", "--tmpfs", "/tmp:rw,nosuid,size=2147483648",
                    "--mount", f"type=bind,src={reports.resolve()},dst=/reports",
                    image, "sh", "-c", script,
                ], timeout=config["per_node_timeout_seconds"],
                    log=reports / "execution.json")
                xml = reports / "tests.xml"
                counts = test_counts(xml) if xml.exists() else None
                variant_outcomes.append({"node": node,
                                         "return_code": executed["return_code"],
                                         "timeout": bool(executed.get("timeout")),
                                         "counts": counts,
                                         "execution_sha256": sha(reports / "execution.json"),
                                         "xml_sha256": sha(xml) if xml.exists() else None})
            outcomes[variant] = variant_outcomes
        buggy_rows, fixed_rows = outcomes["buggy"], outcomes["fixed"]
        reproducible = (
            len(buggy_rows) == len(fixed_rows) == len(nodes) and
            all(row["counts"] is not None and row["counts"]["tests"] > 0 and
                row["counts"]["errors"] == row["counts"]["skipped"] == 0 and
                not row["timeout"] for row in buggy_rows + fixed_rows) and
            any(row["counts"]["failures"] > 0 for row in buggy_rows) and
            all(row["return_code"] == 0 and row["counts"]["failures"] == 0
                for row in fixed_rows))
        record.update(status="reproducible" if reproducible else "environment_excluded",
                      reason=None if reproducible else "all-node buggy/fixed contrast not reproduced",
                      container_image_id=image, test_outcomes=outcomes)
    save_new(out / "preflight_record.json", record)
    return record


def run_next():
    if sys.platform != "linux" or os.geteuid() != 0 or executable() != "podman":
        raise ValueError("Rootful Linux/Podman required")
    state = audit()
    if state["status"] != "preflight_incomplete":
        return state
    import shutil
    if (shutil.disk_usage("/mnt/c").free < 20 * 1024**3 or
            shutil.disk_usage("/mnt/d").free < 100 * 1024**3):
        raise OSError("Storage stop gate reached")
    index = state["attempted"]
    case = read(QUEUE)[index]
    print(json.dumps({"status": "preflight_started",
                      "case_id": f"fastapi_{case['bug_id']}",
                      "provider_calls": 0}), flush=True)
    record = run_one(index, case, read(CONFIG))
    out = RAW / f"{index:02d}_{PROJECT}_{case['bug_id']}"
    row = {"queue_index": index, "case_id": f"fastapi_{case['bug_id']}",
           "selection_hash": case["selection_hash"],
           "status": record["status"], "reason": record["reason"],
           "record_sha256": sha(out / "preflight_record.json"),
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
        "status": freeze()["status"], "lock_sha256": sha(LOCK),
        "provider_calls": 0}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
