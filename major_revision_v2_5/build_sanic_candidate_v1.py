"""Build a gold-free Sanic candidate and public regression verifier in OCI.

The selected preflight case and patch scope are fixed before any LLM call.
The fixed commit is present only in the trusted preflight image for validation;
the candidate image does not inherit that image or contain tests/history.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import sys

import qualify_sanic_v1 as preflight

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
PREVIOUS = V2 / "major_revision_v2_3"
ROOT = HERE / "results/sanic_candidate_v1"
LOCK = ROOT / "lock.json"
CASE_ID = "sanic_5"
BASE = "python:3.8.20-slim-bookworm@sha256:1d52838af602b4b5a831beb13a0e4d073280665ea7be7f69ce2382f29c5a613f"
SETTINGS = {
    "allowed_files": ["sanic/log.py"],
    "public_regression_files": ["tests/test_logging.py"],
    "minimum_active_public_regression_passes": 3,
    "maximum_public_regression_nodes": 10,
    "regression_selection_domain": "cf-v25-sanic-public-regression-20261011",
    "selection_rule": "Hash-sort all non-visible nodes in the declared public test file, take at most ten before outcomes; require at least three active passes on both buggy and fixed",
    "build_timeout_seconds": 600,
    "test_timeout_seconds": 180,
    "provider_calls": 0,
    "paid_execution_allowed": False,
}

sys.path.insert(0, str(PREVIOUS))
from audit_repository_baselines_v2 import dispositions  # noqa: E402
from build_bugsinpy_candidate_v1 import container, image_audit, inspect  # noqa: E402
from container_cli import executable  # noqa: E402
from run_bugsinpy_preflight import execute, test_counts  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def case_spec() -> dict:
    proof = preflight.audit()
    if proof["status"] != "first_case_qualified" or proof["first_qualified_bug_id"] != "5":
        raise ValueError("The predeclared first Sanic case did not qualify")
    item = preflight.read(preflight.QUEUE)["candidates"][0]
    engine_path = preflight.ROOT / "00_sanic_5/engine_ledger.jsonl"
    engine = [json.loads(line) for line in engine_path.read_text(encoding="utf-8").splitlines()
              if line.strip()]
    if len(engine) != 1 or engine[0]["status"] != "reproducible" or (
            engine[0]["selection_hash"] != item["selection_hash"]):
        raise ValueError("Preflight evidence changed")
    record = engine[0]
    artifact = HERE / record["artifact_directory"]
    for key, relative in (("dockerfile_sha256", "Dockerfile"),
                          ("build_report_sha256", "build_report.json"),
                          ("buggy_test_report_sha256", "buggy/execution.json"),
                          ("fixed_test_report_sha256", "fixed/execution.json")):
        if sha256(artifact / relative) != record[key]:
            raise ValueError("Preflight artifact changed: " + key)
    metadata = V2 / "bip/projects/sanic/bugs/5/run_test.sh"
    command = shlex.split(metadata.read_text(encoding="utf-8"))
    if (sha256(metadata) != item["run_test_sha256"] or len(command) != 2 or
            command[0] != "pytest" or command[1] !=
            "tests/test_logging.py::test_logging_modified_root_logger_config"):
        raise ValueError("Visible selector drift")
    return {
        **item, "case_id": CASE_ID, "visible_test": command[1],
        "allowed_files": SETTINGS["allowed_files"],
        "regression_files": SETTINGS["public_regression_files"],
        "validator_source_image": record["container_image_id"],
        "preflight_engine_ledger_sha256": sha256(engine_path),
        "preflight_artifact": record["artifact_directory"],
    }


def stable_lock() -> dict:
    return {
        "status": "v2_5_sanic_gold_free_candidate_frozen_before_provider",
        "case": case_spec(), "settings": SETTINGS,
        "dependencies_sha256": {
            "runner": sha256(Path(__file__)),
            "preflight_lock": sha256(preflight.LOCK),
            "preflight_queue": sha256(preflight.QUEUE),
            "preflight_ledger": sha256(preflight.LEDGER),
            "candidate_helper": sha256(PREVIOUS / "build_bugsinpy_candidate_v1.py"),
            "baseline_helper": sha256(PREVIOUS / "audit_repository_baselines_v2.py"),
        },
        "provider_calls": 0, "paid_execution_allowed": False,
    }


def freeze() -> dict:
    stable = stable_lock()
    if LOCK.exists():
        prior = read(LOCK)
        if any(prior.get(key) != value for key, value in stable.items()):
            raise ValueError("Candidate freeze drift")
        return prior
    if ROOT.exists():
        raise FileExistsError("Candidate root exists without lock")
    ROOT.mkdir(parents=True)
    lock = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, lock)
    return lock


def run_test(image: str, source_root: str, nodes: list[str], output: Path) -> dict:
    command = (f"cp -a {source_root} /tmp/work && cd /tmp/work && "
               "PYTHONPATH=/tmp/work python -m pytest -q " +
               " ".join(shlex.quote(node) for node in nodes) +
               " --junitxml=/reports/tests.xml")
    response, folder = container(image, command, output,
                                 timeout=SETTINGS["test_timeout_seconds"])
    xml = folder / "tests.xml"
    return {
        "return_code": response["return_code"],
        "timeout": bool(response.get("timeout")),
        "counts": test_counts(xml) if xml.exists() else None,
        "dispositions": dispositions(xml) if xml.exists() else {},
        "execution_sha256": sha256(output),
        "xml_sha256": sha256(xml) if xml.exists() else None,
    }


def build() -> dict:
    if sys.platform != "linux" or os.geteuid() != 0 or executable() != "podman":
        raise ValueError("Rootful Linux/Podman required")
    lock = freeze()
    out = ROOT / CASE_ID
    if out.exists():
        if (out / "summary.json").exists():
            return read(out / "summary.json")
        raise FileExistsError("Interrupted candidate build retained; inspect before recovery")
    if shutil.disk_usage("/mnt/c").free < 8 * 1024**3:
        raise OSError("C: below candidate safe-build threshold")
    out.mkdir()
    case = lock["case"]
    dockerfile = (
        f"FROM {case['validator_source_image']} AS trusted\nUSER root\n"
        "RUN mkdir /candidate /protected && cp -a /buggy/sanic /candidate/ && "
        "find /candidate -type d \\( -name tests -o -name test -o -name __pycache__ \\) -prune -exec rm -rf '{}' + && "
        "find /candidate -name .git -delete\n"
        "RUN cp -a /buggy/. /protected/ && rm -f /protected/.git && "
        "find /protected -type d -name __pycache__ -prune -exec rm -rf '{}' +\n"
        f"FROM {BASE} AS candidate\n"
        "COPY --from=trusted /usr/local /usr/local\n"
        "COPY --from=trusted /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu\n"
        "COPY --from=trusted /candidate /candidate\n"
        "ENV PYTHONDONTWRITEBYTECODE=1\nUSER 65534:65534\nWORKDIR /tmp\n"
        "FROM candidate AS verifier\nUSER root\n"
        "COPY --from=trusted /protected /protected\n"
        "USER 65534:65534\nWORKDIR /tmp\n"
    )
    (out / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    images = {}
    for target in ("candidate", "verifier"):
        tag = f"conveyorflow-v25-sanic5-{target}:v1"
        result = execute([executable(), "build", "--target", target, "-t", tag, str(out)],
                         timeout=SETTINGS["build_timeout_seconds"],
                         log=out / f"{target}_build.json")
        if result["return_code"] != 0 or result.get("timeout"):
            raise RuntimeError("Candidate image build failed; preserve artifacts")
        images[target] = inspect(tag)
    candidate_audit = image_audit(images["candidate"], case,
                                  out / "candidate_audit_execution.json")
    command = ("cp -a /protected /tmp/work && cd /tmp/work && "
               "PYTHONPATH=/tmp/work python -m pytest --collect-only -q " +
               " ".join(shlex.quote(path) for path in case["regression_files"]))
    collected, _ = container(images["verifier"], command,
                             out / "regression_collection.json",
                             timeout=SETTINGS["test_timeout_seconds"])
    if collected["return_code"] != 0 or collected.get("timeout"):
        raise RuntimeError("Public regression collection failed; retain artifacts")
    visible = case["visible_test"]
    nodes = sorted(set(line.strip() for line in collected["stdout"].splitlines()
                       if line.startswith("tests/test_logging.py::") and
                       line.strip() != visible),
                   key=lambda node: hashlib.sha256((SETTINGS[
                       "regression_selection_domain"] + "|" + CASE_ID + "|" + node
                   ).encode("utf-8")).hexdigest())
    nodes = nodes[:SETTINGS["maximum_public_regression_nodes"]]
    save_new(out / "regression_selection.json", {
        "case_id": CASE_ID, "nodeids": nodes,
        "selection_rule": SETTINGS["selection_rule"],
        "frozen_before_regression_outcomes": True,
    })
    if len(nodes) < SETTINGS["minimum_active_public_regression_passes"]:
        summary = {"status": "candidate_preflight_failed", "reason": "too_few_public_regressions",
                   "case_id": CASE_ID, "selected_nodes": len(nodes), "images": images,
                   "candidate_audit": candidate_audit, "provider_calls": 0}
        save_new(out / "summary.json", summary)
        return summary
    reports = {
        "buggy_visible": run_test(images["verifier"], "/protected", [visible],
                                  out / "buggy_visible.json"),
        "buggy_regression": run_test(images["verifier"], "/protected", nodes,
                                     out / "buggy_regression.json"),
        "fixed_regression": run_test(case["validator_source_image"], "/fixed", nodes,
                                     out / "fixed_regression.json"),
    }
    vb, bug, fix = (reports[name] for name in (
        "buggy_visible", "buggy_regression", "fixed_regression"))
    active = sum(status == "passed" for status in bug["dispositions"].values())
    passed = (
        vb["return_code"] == 1 and vb["counts"] is not None and
        vb["counts"]["failures"] > 0 and vb["counts"]["errors"] == 0 and
        bug["return_code"] == fix["return_code"] == 0 and
        bug["dispositions"] == fix["dispositions"] and
        len(bug["dispositions"]) == len(nodes) and
        set(bug["dispositions"].values()) <= {"passed", "expected_failure"} and
        active >= SETTINGS["minimum_active_public_regression_passes"] and
        not any(report["timeout"] for report in reports.values())
    )
    summary = {
        "status": "candidate_preflight_passed" if passed else "candidate_preflight_failed",
        "case_id": CASE_ID, "images": images, "candidate_audit": candidate_audit,
        "public_regression_nodeids": nodes, "active_public_regression_passes": active,
        "reports": reports, "lock_sha256": sha256(LOCK),
        "dockerfile_sha256": sha256(out / "Dockerfile"),
        "public_tests_not_novel_hidden_tests": True,
        "provider_calls": 0, "paid_execution_allowed": False,
    }
    save_new(out / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--freeze", action="store_true")
    action.add_argument("--build", action="store_true")
    args = parser.parse_args()
    result = build() if args.build else freeze()
    print(json.dumps({"status": result["status"], "case_id": CASE_ID,
                      "lock_sha256": sha256(LOCK), "provider_calls": 0,
                      "paid_execution_allowed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
