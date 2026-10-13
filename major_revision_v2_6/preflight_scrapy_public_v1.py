"""Run frozen Scrapy BugsInPy public commands on buggy and fixed source.

Source eligibility only: no LLM calls, no model selection and no hidden tests.
Every command in the frozen queue is executed separately in both variants.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

from freeze_scrapy_source_queue_v1 import LOCK as SOURCE_LOCK, QUEUE as SOURCE_QUEUE, freeze as freeze_source

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(V2 / "major_revision_v2_3"))
sys.path.insert(0, str(V2 / "major_revision_v2_5"))
from container_cli import canonical_image_id, executable, runtime_version  # noqa: E402
from run_bugsinpy_preflight import environment, execute  # noqa: E402

ROOT = HERE / "scrapy_public_preflight_v1"
CONFIG, LOCK, LEDGER = (ROOT / name for name in ("config.json", "lock.json", "ledger.jsonl"))
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/scrapy_public_preflight_v1"
RAW = Path(RAW_TEXT if os.name != "nt" else "D:/ConveyorFlowRuntime/v2_6/scrapy_public_preflight_v1")
BASE = "python:3.8.20-slim-bookworm@sha256:1d52838af602b4b5a831beb13a0e4d073280665ea7be7f69ce2382f29c5a613f"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def config() -> dict:
    return {
        "status": "scrapy_public_source_preflight_only",
        "source_url": "https://github.com/scrapy/scrapy.git",
        "base_image": BASE,
        "dependency_profile": [
            "Twisted==20.3.0", "attrs==19.3.0", "Automat==20.2.0",
            "constantly==15.1.0", "cssselect==1.1.0", "hyperlink==19.0.0",
            "incremental==17.5.0", "parsel==1.6.0", "Protego==0.1.16",
            "queuelib==1.5.0", "six==1.15.0", "w3lib==1.22.0",
            "zope.interface==5.1.0", "pyOpenSSL==19.1.0",
            "cryptography==2.9.2", "lxml==4.5.1", "service-identity==18.1.0",
        ],
        "dependency_rule": "Install the listed public core pins, then the buggy Scrapy checkout editable; pip may resolve other package requirements.",
        "environment_deviation": (
            "BugsInPy specifies Python 3.8.3 and a full environment including "
            "Windows-only pywin32/pydivert and unrelated applications. This Linux "
            "preflight uses pinned official Python 3.8.20 plus public Scrapy core "
            "dependency pins, not the entire requirements.txt. The deviation is "
            "frozen before any Scrapy LLM call and does not relax public tests."),
        "selection_rule": "Use frozen hash queue order; keep every exclusion; first two fully reproduced contrasts only",
        "public_test_rule": "Run every declared python -m unittest -q command on both buggy and fixed checkouts",
        "build_timeout_seconds": 2400,
        "per_command_timeout_seconds": 180,
        "provider_calls": 0,
        "paid_execution_allowed": False,
    }


def freeze() -> dict:
    freeze_source()
    stable = {
        "status": "scrapy_public_preflight_frozen_before_provider",
        "source_lock_sha256": sha(SOURCE_LOCK),
        "source_queue_sha256": sha(SOURCE_QUEUE),
        "runner_sha256": sha(Path(__file__)),
        "raw_root": RAW_TEXT,
        "provider_calls": 0,
        "paid_execution_allowed": False,
    }
    desired = config()
    if LOCK.exists():
        old = read(LOCK)
        if (any(old.get(k) != v for k, v in stable.items()) or
                read(CONFIG) != desired or old["config_sha256"] != sha(CONFIG)):
            raise ValueError("Scrapy preflight freeze drift")
        return old
    if ROOT.exists() or RAW.exists():
        raise FileExistsError("Partial preflight root; inspect rather than overwrite")
    ROOT.mkdir()
    RAW.mkdir(parents=True)
    save_new(CONFIG, desired)
    lock = {**stable, "config_sha256": sha(CONFIG),
            "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, lock)
    return lock


def audit() -> dict:
    freeze()
    queue = read(SOURCE_QUEUE)
    rows = [json.loads(line) for line in LEDGER.read_text(
        encoding="utf-8").splitlines() if line.strip()] if LEDGER.exists() else []
    if len(rows) > len(queue):
        raise ValueError("Ledger longer than frozen queue")
    for index, row in enumerate(rows):
        case = queue[index]
        record = RAW / f"{index:02d}_{case['case_id']}/preflight_record.json"
        if (row["queue_index"] != index or row["case_id"] != case["case_id"] or
                row["selection_hash"] != case["selection_hash"] or
                row["record_sha256"] != sha(record) or row["provider_calls"] != 0):
            raise ValueError("Scrapy evidence/ledger drift")
    qualified = [row["case_id"] for row in rows if row["status"] == "reproducible"]
    return {"status": "two_public_contrasts" if len(qualified) == 2 else
            "project_ineligible" if len(rows) == len(queue) else "preflight_incomplete",
            "attempted": len(rows), "qualified_cases": qualified,
            "provider_calls": 0, "lock_sha256": sha(LOCK)}


def parse_unittest(executed: dict) -> dict:
    text = executed.get("stdout", "") + "\n" + executed.get("stderr", "")
    match = re.search(r"Ran (\d+) tests? in", text)
    count = int(match.group(1)) if match else 0
    failed = bool(re.search(r"(?:^|\n)FAILED \(", text))
    okay = bool(re.search(r"(?:^|\n)OK(?:\n|$)", text))
    return {"tests": count, "failed": failed, "okay": okay,
            "return_code": executed["return_code"],
            "timeout": bool(executed.get("timeout"))}


def run_one(index: int, case: dict, cfg: dict) -> dict:
    source = V2 / "bip/projects/scrapy/bugs" / case["bug_id"]
    for name, key in (("bug.info", "bug_info_sha256"),
                      ("requirements.txt", "requirements_sha256"),
                      ("run_test.sh", "run_test_sha256")):
        if sha(source / name) != case[key]:
            raise ValueError("Public metadata drift: " + name)
    for commit in (case["buggy_commit_id"], case["fixed_commit_id_validator_only"]):
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("Invalid frozen commit")
    if not case["public_commands"] or any(
        len(cmd) != 5 or cmd[:4] != ["python", "-m", "unittest", "-q"]
            for cmd in case["public_commands"]):
        raise ValueError("Unsupported frozen public commands")
    out = RAW / f"{index:02d}_{case['case_id']}"
    if out.exists():
        raise FileExistsError("Preflight attempt already exists; inspect before retry")
    out.mkdir()
    deps = " ".join(shlex.quote(item) for item in cfg["dependency_profile"])
    overlay = " && ".join(
        f"git -C /source show {case['fixed_commit_id_validator_only']}:"
        f"{shlex.quote(name)} > /buggy/{shlex.quote(name)}"
        for name in case["test_files"])
    dockerfile = (
        f"FROM {cfg['base_image']}\n"
        "RUN apt-get update && apt-get install -y --no-install-recommends git gcc "
        "libffi-dev libssl-dev libxml2-dev libxslt1-dev && rm -rf /var/lib/apt/lists/*\n"
        "RUN pip install --no-cache-dir 'pip<24' 'setuptools<69' wheel\n"
        f"RUN pip install --no-cache-dir {deps}\n"
        f"RUN git clone --filter=blob:none --no-checkout {cfg['source_url']} /source && "
        f"git -C /source worktree add --detach /buggy {case['buggy_commit_id']} && "
        f"git -C /source worktree add --detach /fixed {case['fixed_commit_id_validator_only']}\n"
        f"RUN {overlay}\n"
        "RUN pip install --no-cache-dir -e /buggy\n"
        "ENV PYTHONDONTWRITEBYTECODE=1\n"
        "USER 65534:65534\nWORKDIR /tmp\n"
    )
    (out / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    tag = f"conveyorflow-v26-scrapy-{case['bug_id']}-preflight:v1"
    built = execute([executable(), "build", "-t", tag, str(out)],
                    timeout=cfg["build_timeout_seconds"], log=out / "build_report.json")
    record = {
        "queue_index": index, "case_id": case["case_id"],
        "selection_hash": case["selection_hash"],
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "runner_sha256": sha(Path(__file__)),
        "dockerfile_sha256": sha(out / "Dockerfile"),
        "build_report_sha256": sha(out / "build_report.json"),
        "original_requirements_sha256": sha(source / "requirements.txt"),
        "public_commands": case["public_commands"],
        "environment_deviation": cfg["environment_deviation"],
        "container_runtime": executable(),
        "runtime_version": runtime_version(environment()),
        "provider_calls": 0,
        "validator_only_image": True,
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
            checks = []
            for command_index, command in enumerate(case["public_commands"]):
                reports = out / variant / f"command_{command_index:02d}"
                reports.mkdir(parents=True)
                script = (f"cp -a /{variant} /tmp/work && cd /tmp/work && "
                          "PYTHONPATH=/tmp/work " + " ".join(shlex.quote(arg) for arg in command))
                executed = execute([
                    executable(), "run", "--rm", "--network", "none", "--read-only",
                    "--cpus", "2", "--memory", "4g", "--pids-limit", "256",
                    "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                    "--user", "65534:65534", "--tmpfs", "/tmp:rw,nosuid,size=2147483648",
                    image, "sh", "-c", script,
                ], timeout=cfg["per_command_timeout_seconds"],
                    log=reports / "execution.json")
                checks.append({"command": command,
                               **parse_unittest(executed),
                               "execution_sha256": sha(reports / "execution.json")})
            outcomes[variant] = checks
        buggy, fixed = outcomes["buggy"], outcomes["fixed"]
        reproducible = (
            len(buggy) == len(fixed) == len(case["public_commands"]) and
            all(row["tests"] > 0 and not row["timeout"] for row in buggy + fixed) and
            any(row["failed"] and row["return_code"] != 0 for row in buggy) and
            all(row["okay"] and row["return_code"] == 0 for row in fixed))
        record.update(status="reproducible" if reproducible else "environment_excluded",
                      reason=None if reproducible else "all-command buggy/fixed contrast not reproduced",
                      container_image_id=image, test_outcomes=outcomes)
    save_new(out / "preflight_record.json", record)
    return record


def run_next() -> dict:
    if sys.platform != "linux" or os.geteuid() != 0 or executable() != "podman":
        raise ValueError("Rootful Linux/Podman required")
    state = audit()
    if state["status"] != "preflight_incomplete":
        return state
    if (shutil.disk_usage("/mnt/c").free < 20 * 1024**3 or
            shutil.disk_usage("/mnt/d").free < 100 * 1024**3):
        raise OSError("Storage stop gate reached")
    index = state["attempted"]
    case = read(SOURCE_QUEUE)[index]
    print(json.dumps({"status": "preflight_started", "case_id": case["case_id"],
                      "provider_calls": 0}), flush=True)
    record = run_one(index, case, read(CONFIG))
    out = RAW / f"{index:02d}_{case['case_id']}"
    row = {"queue_index": index, "case_id": case["case_id"],
           "selection_hash": case["selection_hash"],
           "status": record["status"], "reason": record["reason"],
           "record_sha256": sha(out / "preflight_record.json"),
           "provider_calls": 0}
    with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--audit", action="store_true")
    modes.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    output = run_next() if args.run_next else audit() if args.audit else {
        "status": freeze()["status"], "lock_sha256": sha(LOCK), "provider_calls": 0}
    print(json.dumps(output, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
