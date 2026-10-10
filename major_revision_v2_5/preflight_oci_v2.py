"""Container-only BugsInPy preflight with safe test-command normalization.

Amends the v2.3 engine's OCI tag construction for mixed-case project names.
No case or outcome selection is performed here; the caller owns a frozen queue.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess

from run_bugsinpy_preflight import environment, execute, test_counts
from container_cli import canonical_image_id, executable, runtime_version


V2 = Path(__file__).resolve().parent.parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_test(case: dict, script: Path) -> str:
    args = shlex.split(script.read_text(encoding="utf-8").strip())
    test_file = PurePosixPath(case["test_file"])
    if test_file.is_absolute() or ".." in test_file.parts or not str(test_file).endswith(".py"):
        raise ValueError("Unsafe test path")
    if len(args) == 2 and args[0] == "pytest":
        node = args[1]
    elif len(args) == 4 and args[:3] == ["pytest", "-q", "-s"]:
        node = args[3]
    elif len(args) == 5 and args[:4] == ["python", "-m", "unittest", "-q"]:
        dotted = args[4]
        stem = str(test_file)[:-3].replace("/", ".")
        if not dotted.startswith(stem + "."):
            raise ValueError("Unittest module and frozen test_file differ")
        node = str(test_file) + "::" + "::".join(dotted[len(stem) + 1:].split("."))
    else:
        raise ValueError("Unsupported public test command")
    if not node.startswith(str(test_file) + "::") or any(c in node for c in (";", "`", "\n", "\r")):
        raise ValueError("Unsafe or mismatched public test selector")
    return node


def run_one(case: dict, config: dict, out: Path) -> dict:
    project, bug_id = case["project"], str(case["bug_id"])
    metadata = V2 / "bip/projects" / project / "bugs" / bug_id
    if (sha256(metadata / "bug.info") != case["bug_info_sha256"] or
            sha256(metadata / "run_test.sh") != case["run_test_sha256"]):
        raise ValueError("Frozen public metadata changed")
    node = normalized_test(case, metadata / "run_test.sh")
    profile = config["profiles"][project]
    if not case["python_version"].startswith(config["python_scope"] + "."):
        raise ValueError("Python version outside frozen scope")
    buggy, fixed = case["buggy_commit_id"], case["fixed_commit_id_for_validator_only"]
    if not re.fullmatch(r"[0-9a-f]{7,40}", buggy) or not re.fullmatch(r"[0-9a-f]{40}", fixed):
        raise ValueError("Invalid frozen source commit")
    if out.exists():
        raise FileExistsError("Prior case attempt retained; inspect before rerun")
    out.mkdir(parents=True)
    base = config["base_image"]
    packages = " ".join(shlex.quote(item) for item in config["common_packages"])
    dependencies = " ".join(shlex.quote(item) for item in profile["packages"])
    dockerfile = (
        f"FROM {base}\n"
        f"ENV CFLAGS={shlex.quote(config['compile_flags'])} "
        f"CXXFLAGS={shlex.quote(config['compile_flags'])}\n"
        "RUN apt-get update && apt-get install -y --no-install-recommends "
        "git build-essential libfreetype6-dev libpng-dev pkg-config && "
        "rm -rf /var/lib/apt/lists/*\n"
        f"RUN pip install --no-cache-dir {packages} && pip install --no-cache-dir {dependencies}\n"
        f"RUN git clone --filter=blob:none --no-checkout {shlex.quote(profile['url'])} /source && "
        f"git -C /source worktree add --detach /buggy {buggy} && "
        f"git -C /source worktree add --detach /fixed {fixed}\n"
        f"RUN git -C /source show {fixed}:{shlex.quote(str(case['test_file']))} "
        f"> /buggy/{shlex.quote(str(case['test_file']))}\n"
        f"RUN cd /buggy && {profile['build']}\n"
        f"RUN cd /fixed && {profile['build']}\n"
        "ENV PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg\n"
        "USER 65534:65534\nWORKDIR /tmp\n"
    )
    (out / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    # OCI reference repositories must be lowercase even when BugsInPy's
    # canonical project directory is mixed-case (e.g. PySnooper).
    tag = f"conveyorflow-bip-{project.lower()}-{bug_id}-preflight:v2.5"
    build = execute([executable(), "build", "-t", tag, str(out)],
                    timeout=config["build_timeout_seconds"], log=out / "build_report.json")
    record = {
        "project": project, "bug_id": bug_id, "selection_hash": case["selection_hash"],
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "runner_sha256": sha256(Path(__file__)),
        "dockerfile_sha256": sha256(out / "Dockerfile"),
        "build_report_sha256": sha256(out / "build_report.json"),
        "original_requirements_sha256": sha256(metadata / "requirements.txt"),
        "normalized_public_test_node": node,
        "environment_deviation": config["environment_deviation"],
        "container_runtime": executable(), "runtime_version": runtime_version(environment()),
        "provider_calls": 0, "validator_only_image": True,
    }
    if build["return_code"] != 0 or build.get("timeout"):
        record.update(status="environment_excluded", reason="container build failed or timed out")
    else:
        inspected = subprocess.run([executable(), "image", "inspect", tag, "--format", "{{.Id}}"],
                                   capture_output=True, text=True, timeout=30, check=True,
                                   env=environment())
        image = canonical_image_id(inspected.stdout)
        outcomes = {}
        for variant in ("buggy", "fixed"):
            reports = out / variant
            reports.mkdir()
            script = (f"cp -a /{variant} /tmp/work && cd /tmp/work && "
                      "PYTHONPATH=/tmp/work:/tmp/work/lib python -m pytest -q "
                      f"{shlex.quote(node)} --junitxml=/reports/tests.xml")
            run = execute([
                executable(), "run", "--rm", "--network", "none", "--read-only",
                "--cpus", "2", "--memory", "4g", "--pids-limit", "256",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--user", "65534:65534", "--tmpfs", "/tmp:rw,nosuid,size=2147483648",
                "--mount", f"type=bind,src={reports.resolve()},dst=/reports",
                image, "sh", "-c", script,
            ], timeout=config["test_timeout_seconds"], log=reports / "execution.json")
            outcomes[variant] = {"return_code": run["return_code"],
                                 **test_counts(reports / "tests.xml")}
        bug, fix = outcomes["buggy"], outcomes["fixed"]
        reproducible = (
            bug["return_code"] == 1 and bug["failures"] > 0 and bug["errors"] == 0 and
            fix["return_code"] == 0 and fix["tests"] > fix["skipped"] and
            fix["failures"] == 0 and fix["errors"] == 0
        )
        record.update(
            status="reproducible" if reproducible else "environment_excluded",
            reason=None if reproducible else "buggy/fixed test contrast not reproduced",
            container_image_id=image, test_outcomes=outcomes,
            buggy_test_report_sha256=sha256(out / "buggy/execution.json"),
            fixed_test_report_sha256=sha256(out / "fixed/execution.json"),
        )
    with (out / "preflight_record.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return record
