"""Gold-free candidate and public-regression gate for PySnooper bug 3.

The allowed production file follows the buggy traceback. Fixed source and
public tests are absent from the candidate image seen by a later model.
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

import qualify_pysnooper_v1 as cohort
import qualify_pysnooper_v1d as preflight

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
PREVIOUS = V2 / "major_revision_v2_3"
ROOT = HERE / "results/pysnooper_candidate_v1"
LOCK = ROOT / "lock.json"
CASE_ID = "PySnooper_3"
BASE = "python:3.8.20-slim-bookworm@sha256:1d52838af602b4b5a831beb13a0e4d073280665ea7be7f69ce2382f29c5a613f"
SETTINGS = {
    "allowed_files": ["pysnooper/pysnooper.py"],
    "public_regression_files": ["tests/test_pysnooper.py"],
    "maximum_public_regression_nodes": 10,
    "minimum_active_public_regression_passes": 5,
    "selection_domain": "cf-v25-pysnooper-public-regression-20261011",
    "rule": "Hash-sort non-visible public tests from the declared file; take first ten before outcomes; require five active common passes",
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
    audit = preflight.audit()
    if audit["status"] != "first_case_qualified" or audit["first_qualified_bug_id"] != "3":
        raise ValueError("First frozen PySnooper case not qualified")
    item = read(cohort.QUEUE)["candidates"][0]
    record_path = preflight.ROOT / "00_pysnooper_3/preflight_record.json"
    record = read(record_path)
    if (record["status"] != "reproducible" or
            record["selection_hash"] != item["selection_hash"] or
            sha256(record_path) != preflight.records()[0]["record_sha256"]):
        raise ValueError("Container preflight proof drift")
    artifact = record_path.parent
    for key, relative in (("dockerfile_sha256", "Dockerfile"),
                          ("build_report_sha256", "build_report.json"),
                          ("buggy_test_report_sha256", "buggy/execution.json"),
                          ("fixed_test_report_sha256", "fixed/execution.json")):
        if sha256(artifact / relative) != record[key]:
            raise ValueError("Preflight artifact drift: " + key)
    if record["normalized_public_test_node"] != "tests/test_pysnooper.py::test_file_output":
        raise ValueError("Visible test identity drift")
    return {
        **item, "case_id": CASE_ID,
        "visible_test": record["normalized_public_test_node"],
        "allowed_files": SETTINGS["allowed_files"],
        "regression_files": SETTINGS["public_regression_files"],
        "validator_source_image": record["container_image_id"],
        "preflight_record_sha256": sha256(record_path),
    }


def freeze() -> dict:
    stable = {
        "status": "v2_5_pysnooper_gold_free_candidate_frozen_before_provider",
        "case": case_spec(), "settings": SETTINGS,
        "dependencies_sha256": {
            "runner": sha256(Path(__file__)),
            "cohort_queue": sha256(cohort.QUEUE),
            "preflight_lock": sha256(preflight.LOCK),
            "preflight_ledger": sha256(preflight.LEDGER),
            "candidate_helper": sha256(PREVIOUS / "build_bugsinpy_candidate_v1.py"),
            "baseline_helper": sha256(PREVIOUS / "audit_repository_baselines_v2.py"),
        },
        "provider_calls": 0, "paid_execution_allowed": False,
    }
    if LOCK.exists():
        prior = read(LOCK)
        if any(prior.get(key) != value for key, value in stable.items()):
            raise ValueError("Frozen candidate drift")
        return prior
    if ROOT.exists():
        raise FileExistsError("Candidate root exists without lock")
    ROOT.mkdir(parents=True)
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def test_run(image: str, source: str, nodes: list[str], output: Path) -> dict:
    command = (f"cp -a {source} /tmp/work && cd /tmp/work && "
               "PYTHONPATH=/tmp/work python -m pytest -q " +
               " ".join(shlex.quote(node) for node in nodes) +
               " --junitxml=/reports/tests.xml")
    result, reports = container(image, command, output,
                                timeout=SETTINGS["test_timeout_seconds"])
    xml = reports / "tests.xml"
    return {
        "return_code": result["return_code"], "timeout": bool(result.get("timeout")),
        "counts": test_counts(xml) if xml.exists() else None,
        "dispositions": dispositions(xml) if xml.exists() else {},
        "execution_sha256": sha256(output),
        "xml_sha256": sha256(xml) if xml.exists() else None,
    }


def build() -> dict:
    if sys.platform != "linux" or os.geteuid() != 0 or executable() != "podman":
        raise ValueError("Rootful Linux/Podman required")
    frozen = freeze()
    out = ROOT / CASE_ID
    if out.exists():
        if (out / "summary.json").exists():
            return read(out / "summary.json")
        raise FileExistsError("Interrupted candidate build retained")
    if shutil.disk_usage("/mnt/c").free < 8 * 1024**3:
        raise OSError("C: below safe build threshold")
    out.mkdir()
    case = frozen["case"]
    dockerfile = (
        f"FROM {case['validator_source_image']} AS trusted\nUSER root\n"
        "RUN mkdir /candidate /protected && cp -a /buggy/pysnooper /candidate/ && "
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
        tag = f"conveyorflow-v25-pysnooper3-{target}:v1"
        response = execute([executable(), "build", "--target", target, "-t", tag, str(out)],
                           timeout=SETTINGS["build_timeout_seconds"],
                           log=out / f"{target}_build.json")
        if response["return_code"] != 0 or response.get("timeout"):
            raise RuntimeError("Candidate image build failed; artifacts retained")
        images[target] = inspect(tag)
    candidate_audit = image_audit(images["candidate"], case,
                                  out / "candidate_audit_execution.json")
    collect = ("cp -a /protected /tmp/work && cd /tmp/work && "
               "PYTHONPATH=/tmp/work python -m pytest --collect-only -q "
               "tests/test_pysnooper.py")
    collected, _ = container(images["verifier"], collect,
                             out / "regression_collection.json",
                             timeout=SETTINGS["test_timeout_seconds"])
    if collected["return_code"] != 0 or collected.get("timeout"):
        raise RuntimeError("Public regression collection failed; artifacts retained")
    visible = case["visible_test"]
    nodes = sorted(set(line.strip() for line in collected["stdout"].splitlines()
                       if line.startswith("tests/test_pysnooper.py::") and
                       line.strip() != visible),
                   key=lambda node: hashlib.sha256((SETTINGS["selection_domain"] +
                                                    "|" + CASE_ID + "|" + node).encode()).hexdigest())
    nodes = nodes[:SETTINGS["maximum_public_regression_nodes"]]
    save_new(out / "regression_selection.json", {
        "case_id": CASE_ID, "nodeids": nodes, "rule": SETTINGS["rule"],
        "frozen_before_test_outcomes": True,
    })
    if len(nodes) < SETTINGS["minimum_active_public_regression_passes"]:
        summary = {"status": "candidate_preflight_failed", "reason": "too_few_regressions",
                   "case_id": CASE_ID, "selected": len(nodes), "images": images,
                   "candidate_audit": candidate_audit, "provider_calls": 0}
        save_new(out / "summary.json", summary)
        return summary
    reports = {
        "buggy_visible": test_run(images["verifier"], "/protected", [visible],
                                  out / "buggy_visible.json"),
        "buggy_regression": test_run(images["verifier"], "/protected", nodes,
                                     out / "buggy_regression.json"),
        "fixed_regression": test_run(case["validator_source_image"], "/fixed", nodes,
                                     out / "fixed_regression.json"),
    }
    visible_report = reports["buggy_visible"]
    buggy, fixed = reports["buggy_regression"], reports["fixed_regression"]
    active = sum(status == "passed" for status in buggy["dispositions"].values())
    passed = (
        visible_report["return_code"] == 1 and visible_report["counts"] is not None and
        visible_report["counts"]["failures"] > 0 and visible_report["counts"]["errors"] == 0 and
        buggy["return_code"] == fixed["return_code"] == 0 and
        buggy["dispositions"] == fixed["dispositions"] and
        len(buggy["dispositions"]) == len(nodes) and
        set(buggy["dispositions"].values()) <= {"passed", "expected_failure"} and
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
