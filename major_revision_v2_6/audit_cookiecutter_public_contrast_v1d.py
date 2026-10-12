"""Independent, read-only audit of Cookiecutter case 3 public contrast.

This is not a gold-free candidate audit and does not qualify the project for
the v2.6 main cohort. It verifies raw test XML and hashes without Podman/LLM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE / "cookiecutter_preflight_v1d"
RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_6/cookiecutter_preflight_v1d"
           if os.name != "nt" else "D:/ConveyorFlowRuntime/v2_6/cookiecutter_preflight_v1d")
CASE = RAW / "00_cookiecutter_3"
CAPSULE = HERE / "cookiecutter_public_contrast_capsule_v1d.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str):
    if not condition:
        raise ValueError(message)


def junit_counts(path: Path):
    root = ET.parse(path).getroot()
    cases = root.findall(".//testcase")
    return {
        "tests": len(cases),
        "failures": sum(bool(case.findall("failure")) for case in cases),
        "errors": sum(bool(case.findall("error")) for case in cases),
        "skipped": sum(bool(case.findall("skipped")) for case in cases),
    }


def audit():
    lock, record = read(ROOT / "lock.json"), read(CASE / "preflight_record.json")
    queue, config = read(ROOT / "queue.json"), read(ROOT / "config.json")
    ledger = [json.loads(line) for line in (ROOT / "ledger.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    require(len(ledger) == 1 and len(queue) == 4, "Unexpected queue/ledger length")
    require(lock["queue_sha256"] == sha(ROOT / "queue.json") and
            lock["config_sha256"] == sha(ROOT / "config.json") and
            lock["runner_sha256"] == sha(HERE / "preflight_cookiecutter_v1d.py"),
            "Frozen input or runner hash drift")
    require(lock["provider_calls"] == record["provider_calls"] == ledger[0]["provider_calls"] == 0,
            "Unexpected provider call")
    require(ledger[0]["case_id"] == "cookiecutter_3" and
            ledger[0]["record_sha256"] == sha(CASE / "preflight_record.json") and
            ledger[0]["selection_hash"] == queue[0]["selection_hash"] ==
            record["selection_hash"], "Selection/evidence mismatch")
    require(config["base_image"].startswith("docker.io/library/python:3.6.15-slim-buster@sha256:"),
            "Base image drift")
    for key, path in (
        ("dockerfile_sha256", CASE / "Dockerfile"),
        ("build_report_sha256", CASE / "build_report.json"),
        ("buggy_test_report_sha256", CASE / "buggy/execution.json"),
        ("fixed_test_report_sha256", CASE / "fixed/execution.json"),
    ):
        require(record[key] == sha(path), f"{key} drift")
    dockerfile = (CASE / "Dockerfile").read_text(encoding="utf-8")
    for marker in ("archive.debian.org", "pytest-cov==2.10.1", "pytest-mock==3.3.1"):
        require(marker in dockerfile, f"Missing frozen dependency: {marker}")
    require(record["status"] == "reproducible" and
            record["normalized_public_test_node"] ==
            "tests/test_read_user_choice.py::test_click_invocation", "Record status/node drift")
    outcomes = {}
    for variant in ("buggy", "fixed"):
        counts = junit_counts(CASE / variant / "tests.xml")
        observed = record["test_outcomes"][variant]
        require(counts == {key: observed[key] for key in counts}, f"{variant} JUnit mismatch")
        execution = read(CASE / variant / "execution.json")
        require(execution["return_code"] == observed["return_code"],
                f"{variant} return code mismatch")
        outcomes[variant] = observed
    require(outcomes["buggy"] == {"tests": 4, "failures": 4, "errors": 0,
                                  "skipped": 0, "return_code": 1} and
            outcomes["fixed"] == {"tests": 4, "failures": 0, "errors": 0,
                                  "skipped": 0, "return_code": 0},
            "Buggy/fixed public contrast not confirmed")
    return {
        "status": "public_contrast_audited_not_candidate_qualified",
        "case_id": "cookiecutter_3",
        "project_eligible_for_main": False,
        "provider_calls": 0,
        "buggy": outcomes["buggy"],
        "fixed": outcomes["fixed"],
        "image_id": record["container_image_id"],
        "lock_sha256": sha(ROOT / "lock.json"),
        "ledger_sha256": sha(ROOT / "ledger.jsonl"),
        "record_sha256": sha(CASE / "preflight_record.json"),
        "environment_deviation": record["environment_deviation"],
        "raw_root": str(RAW),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    summary = audit()
    if args.write:
        if CAPSULE.exists():
            require(read(CAPSULE) == summary, "Existing capsule drift")
        else:
            with CAPSULE.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(summary, stream, indent=2, sort_keys=True)
                stream.write("\n")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
