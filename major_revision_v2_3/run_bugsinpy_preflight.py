"""Ordered, container-only BugsInPy environment preflight without LLM calls.

The image is validator-only: it contains both commits and must never be given
to an LLM candidate. Only a reproducible buggy/fixed test contrast can qualify.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from select_bugsinpy_pilot import MANIFEST, select
from container_cli import executable, runtime_version, canonical_image_id


HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config_bugsinpy_preflight_v1.json"
LEDGER = HERE / "results" / "bugsinpy_preflight_ledger.jsonl"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def environment() -> dict:
    return {key: value for key, value in os.environ.items()
            if key != "MFEC_LITELLM_API_KEY"}


def execute(command: list[str], *, timeout: int, log: Path) -> dict:
    started = time.monotonic()
    try:
        process = subprocess.run(command, capture_output=True, text=True,
                                 errors="replace", timeout=timeout, env=environment())
        result = {"return_code": process.returncode,
                  "stdout": process.stdout, "stderr": process.stderr}
    except subprocess.TimeoutExpired as error:
        def decoded(value):
            return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
        result = {"return_code": None, "timeout": True,
                  "stdout": decoded(error.stdout), "stderr": decoded(error.stderr)}
    result["elapsed_seconds"] = time.monotonic() - started
    log.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def test_counts(path: Path) -> dict:
    if not path.is_file():
        return {"tests": 0, "failures": 0, "errors": 1, "skipped": 0}
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    return {key: sum(int(suite.get(key, "0")) for suite in suites)
            for key in ("tests", "failures", "errors", "skipped")}


def run_next(config_path: Path = CONFIG, ledger: Path = LEDGER,
             artifact_prefix: str = "bugsinpy_preflight_v1") -> dict:
    config_path, ledger = config_path.resolve(), ledger.resolve()
    if not config_path.is_relative_to(HERE) or not ledger.is_relative_to(HERE):
        raise ValueError("config and ledger must stay in the v2.3 workstream")
    if not re.fullmatch(r"[A-Za-z0-9_]+", artifact_prefix):
        raise ValueError("invalid artifact directory label")
    settings = json.loads(config_path.read_text(encoding="utf-8"))
    selection = select(MANIFEST, ledger)
    if selection["selected"]:
        return selection
    index = selection["preflighted_in_frozen_order"]
    if index >= settings["max_candidates"]:
        raise RuntimeError("frozen preflight candidate budget exhausted")
    candidates = json.loads(MANIFEST.read_text(encoding="utf-8"))["candidates"]
    item = candidates[index]
    project, bug_id = item["project"], item["bug_id"]
    metadata = HERE.parent / "bip" / "projects" / project / "bugs" / bug_id
    if (sha256(metadata / "bug.info") != item["bug_info_sha256"]
            or sha256(metadata / "run_test.sh") != item["run_test_sha256"]):
        raise ValueError("frozen metadata changed")
    profile = settings["profiles"].get(project)
    if profile is None or not item["python_version"].startswith(settings["python_scope"] + "."):
        raise RuntimeError(f"environment profile not yet implemented for {project} Python {item['python_version']}; candidate is not silently excluded")
    buggy = item["buggy_commit_id"]
    fixed = item["fixed_commit_id_for_validator_only"]
    if not re.fullmatch(r"[0-9a-f]{7,40}", buggy) or not re.fullmatch(r"[0-9a-f]{40}", fixed):
        raise ValueError("invalid commit identity")
    test_file = PurePosixPath(item["test_file"])
    if test_file.is_absolute() or ".." in test_file.parts:
        raise ValueError("invalid test path")
    command = shlex.split((metadata / "run_test.sh").read_text(encoding="utf-8").strip())
    if len(command) != 2 or command[0] != "pytest" or not command[1].startswith(str(test_file)):
        raise RuntimeError("test command requires explicit harness support")
    runtime = runtime_version(environment())
    output = HERE / "results" / artifact_prefix / f"{index:03d}_{project}_{bug_id}"
    if output.exists():
        raise FileExistsError("prior preflight artifacts exist; inspect/recover rather than overwrite")
    output.mkdir(parents=True)
    packages = " ".join(shlex.quote(value) for value in settings["common_packages"])
    dependencies = " ".join(shlex.quote(value) for value in profile["packages"])
    dockerfile = (
        f"FROM {settings['base_image']}\n"
        + (f"ENV CFLAGS={shlex.quote(settings['compile_flags'])} CXXFLAGS={shlex.quote(settings['compile_flags'])}\n"
           if settings.get("compile_flags") else "") +
        "RUN apt-get update && apt-get install -y --no-install-recommends git build-essential libfreetype6-dev libpng-dev pkg-config && rm -rf /var/lib/apt/lists/*\n"
        f"RUN pip install --no-cache-dir {packages} && pip install --no-cache-dir {dependencies}\n"
        f"RUN git clone --filter=blob:none --no-checkout {profile['url']} /source && git -C /source worktree add --detach /buggy {buggy} && git -C /source worktree add --detach /fixed {fixed}\n"
        f"RUN git -C /source show {fixed}:{test_file} > /buggy/{test_file}\n"
        f"RUN cd /buggy && {profile['build']}\n"
        f"RUN cd /fixed && {profile['build']}\n"
        "ENV PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg\n"
        "USER 65534:65534\nWORKDIR /tmp\n"
    )
    (output / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    tag = f"conveyorflow-bip-{project}-{bug_id}-preflight:v2.3"
    build_command = [executable(), "build"]
    if executable() == "docker":
        build_command += ["--progress", "plain"]
    build = execute(build_command + ["-t", tag, str(output)],
                    timeout=settings["build_timeout_seconds"], log=output / "build_report.json")
    record = {
        "project": project, "bug_id": bug_id, "selection_hash": item["selection_hash"],
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": sha256(config_path), "runner_sha256": sha256(Path(__file__)),
        "dockerfile_sha256": sha256(output / "Dockerfile"),
        "build_report_sha256": sha256(output / "build_report.json"),
        "original_requirements_sha256": sha256(metadata / "requirements.txt"),
        "no_llm_calls": True, "validator_only_image": True,
        "environment_deviation": settings["environment_deviation"],
        "artifact_directory": str(output.relative_to(HERE)),
        "container_runtime": executable(), "runtime_version": runtime,
    }
    if build["return_code"] != 0:
        record.update(status="environment_excluded", reason="container build failed or timed out; see preserved build_report.json")
    else:
        inspected = subprocess.run([executable(), "image", "inspect", tag, "--format", "{{.Id}}"],
                                   capture_output=True, text=True, timeout=30, check=True, env=environment())
        image = canonical_image_id(inspected.stdout)
        outcomes = {}
        for variant in ("buggy", "fixed"):
            report_dir = output / variant
            report_dir.mkdir()
            script = (f"cp -a /{variant} /tmp/work && cd /tmp/work && "
                      f"PYTHONPATH=/tmp/work:/tmp/work/lib python -m pytest -q {shlex.quote(command[1])} --junitxml=/reports/tests.xml")
            run = execute([
                executable(), "run", "--rm", "--network", "none", "--read-only",
                "--cpus", "2", "--memory", "4g", "--pids-limit", "256",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--user", "65534:65534", "--tmpfs", "/tmp:rw,nosuid,size=2147483648",
                "--mount", f"type=bind,src={report_dir.resolve()},dst=/reports",
                image, "sh", "-c", script,
            ], timeout=settings["test_timeout_seconds"], log=report_dir / "execution.json")
            outcomes[variant] = {"return_code": run["return_code"], **test_counts(report_dir / "tests.xml")}
        bug, fix = outcomes["buggy"], outcomes["fixed"]
        reproducible = (bug["return_code"] == 1 and bug["failures"] > 0 and bug["errors"] == 0
                        and fix["return_code"] == 0 and fix["tests"] > fix["skipped"]
                        and fix["failures"] == 0 and fix["errors"] == 0)
        record.update(container_image_id=image, test_outcomes=outcomes,
                      buggy_test_report_sha256=sha256(output / "buggy" / "execution.json"),
                      fixed_test_report_sha256=sha256(output / "fixed" / "execution.json"))
        if reproducible:
            record.update(status="reproducible", buggy_test_failed=True, fixed_test_passed=True)
        else:
            record.update(status="environment_excluded", reason="buggy/fixed relevant test contrast not reproduced under declared environment; see test reports")
    (output / "preflight_record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return {"record": record, "selection": select(MANIFEST, ledger)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    parser.add_argument("--artifact-prefix", default="bugsinpy_preflight_v1")
    args = parser.parse_args()
    result = run_next(args.config, args.ledger, args.artifact_prefix)
    print(json.dumps(result, indent=2))
