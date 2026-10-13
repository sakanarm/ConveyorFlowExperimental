"""Read-only audit of both frozen Cookiecutter public buggy/fixed contrasts.

This post-preflight audit checks evidence integrity and test outcomes. It is
not a gold-free candidate audit and does not qualify Cookiecutter for main.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_cookiecutter_public_contrast_v1d import (
    HERE, RAW, ROOT, junit_counts, read, require, sha,
)

CAPSULE = HERE / "cookiecutter_two_public_contrasts_capsule_v1.json"


def audit():
    lock, queue, config = (read(ROOT / name) for name in
                           ("lock.json", "queue.json", "config.json"))
    ledger = [json.loads(line) for line in (ROOT / "ledger.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    require(len(queue) == 4 and len(ledger) == 2, "Frozen queue/ledger length")
    require(lock["queue_sha256"] == sha(ROOT / "queue.json") and
            lock["config_sha256"] == sha(ROOT / "config.json") and
            lock["runner_sha256"] == sha(HERE / "preflight_cookiecutter_v1d.py"),
            "Frozen input or runner drift")
    require(lock["provider_calls"] == 0 and
            config["base_image"].startswith(
                "docker.io/library/python:3.6.15-slim-buster@sha256:"),
            "Provider/base image drift")

    cases = []
    for index, expected_id in enumerate(("cookiecutter_3", "cookiecutter_1")):
        item, row = queue[index], ledger[index]
        case_dir = RAW / f"{index:02d}_{expected_id}"
        record = read(case_dir / "preflight_record.json")
        require(row["queue_index"] == index and row["case_id"] == expected_id
                and row["selection_hash"] == item["selection_hash"]
                == record["selection_hash"] and
                row["record_sha256"] == sha(case_dir / "preflight_record.json"),
                f"{expected_id} selection/evidence drift")
        require(row["status"] == record["status"] == "reproducible" and
                row["provider_calls"] == record["provider_calls"] == 0,
                f"{expected_id} status/provider drift")
        for key, path in (
            ("dockerfile_sha256", case_dir / "Dockerfile"),
            ("build_report_sha256", case_dir / "build_report.json"),
            ("buggy_test_report_sha256", case_dir / "buggy/execution.json"),
            ("fixed_test_report_sha256", case_dir / "fixed/execution.json"),
        ):
            require(record[key] == sha(path), f"{expected_id} {key} drift")
        dockerfile = (case_dir / "Dockerfile").read_text(encoding="utf-8")
        for marker in ("archive.debian.org", "pytest-cov==2.10.1",
                       "pytest-mock==3.3.1"):
            require(marker in dockerfile, f"{expected_id} dependency drift: {marker}")
        outcomes = {}
        for variant in ("buggy", "fixed"):
            counts = junit_counts(case_dir / variant / "tests.xml")
            observed = record["test_outcomes"][variant]
            require(counts == {key: observed[key] for key in counts} and
                    read(case_dir / variant / "execution.json")["return_code"]
                    == observed["return_code"],
                    f"{expected_id} {variant} XML/execution mismatch")
            outcomes[variant] = observed
        buggy, fixed = outcomes["buggy"], outcomes["fixed"]
        require(buggy["tests"] > 0 and buggy["failures"] > 0 and
                buggy["errors"] == buggy["skipped"] == 0 and
                buggy["return_code"] != 0 and
                fixed["tests"] == buggy["tests"] and
                fixed["failures"] == fixed["errors"] == fixed["skipped"] == 0
                and fixed["return_code"] == 0,
                f"{expected_id} public contrast failed")
        cases.append({"case_id": expected_id,
                      "record_sha256": row["record_sha256"],
                      "public_test_node": record["normalized_public_test_node"],
                      "buggy": buggy, "fixed": fixed})

    return {"status": "two_public_contrasts_audited_not_candidate_qualified",
            "project_eligible_for_main": False, "provider_calls": 0,
            "cases": cases, "lock_sha256": sha(ROOT / "lock.json"),
            "ledger_sha256": sha(ROOT / "ledger.jsonl"),
            "raw_root": str(RAW)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.write:
        if CAPSULE.exists():
            require(read(CAPSULE) == result, "Existing capsule drift")
        else:
            with CAPSULE.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(result, stream, indent=2, sort_keys=True)
                stream.write("\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
