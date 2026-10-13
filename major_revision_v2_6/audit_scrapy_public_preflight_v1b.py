"""Independent persisted-evidence check for the two Scrapy source contrasts.

No provider, network, or container calls are made by this audit.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


HERE = Path(__file__).resolve().parent
QUEUE = HERE / "scrapy_source_queue_v1/queue.json"
ROOT = HERE / "scrapy_public_preflight_v1b"
RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_6/scrapy_public_preflight_v1b")
if not RAW.exists():
    RAW = Path("D:/ConveyorFlowRuntime/v2_6/scrapy_public_preflight_v1b")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def audit() -> dict:
    lock, queue = read(ROOT / "lock.json"), read(QUEUE)
    rows = [json.loads(line) for line in (ROOT / "ledger.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    assert lock["source_queue_sha256"] == sha(QUEUE)
    assert lock["config_sha256"] == sha(ROOT / "config.json")
    assert len(rows) == 2 and [row["case_id"] for row in rows] == [
        "scrapy_39", "scrapy_34"]
    observations = []
    for index, row in enumerate(rows):
        case = queue[index]
        folder = RAW / f"{index:02d}_{case['case_id']}"
        record_path = folder / "preflight_record.json"
        record = read(record_path)
        assert row["queue_index"] == record["queue_index"] == index
        assert row["case_id"] == record["case_id"] == case["case_id"]
        assert row["selection_hash"] == case["selection_hash"]
        assert row["record_sha256"] == sha(record_path)
        assert row["status"] == record["status"] == "reproducible"
        assert row["provider_calls"] == record["provider_calls"] == 0
        assert record["public_commands"] == case["public_commands"]
        assert record["dockerfile_sha256"] == sha(folder / "Dockerfile")
        assert record["build_report_sha256"] == sha(folder / "build_report.json")
        assert record["container_image_id"].startswith("sha256:")
        counts = {}
        for variant in ("buggy", "fixed"):
            reported = record["test_outcomes"][variant]
            assert len(reported) == len(case["public_commands"])
            counts[variant] = 0
            for command_index, expected in enumerate(case["public_commands"]):
                one = reported[command_index]
                execution_path = folder / variant / f"command_{command_index:02d}/execution.json"
                execution = read(execution_path)
                transcript = execution["stdout"] + "\n" + execution["stderr"]
                match = re.search(r"Ran (\d+) tests? in", transcript)
                assert one["command"] == expected
                assert one["execution_sha256"] == sha(execution_path)
                assert match is not None and one["tests"] == int(match.group(1)) == 1
                assert not one["timeout"]
                assert "_FailedTest" not in transcript
                assert "ModuleNotFoundError" not in transcript
                if variant == "buggy":
                    assert one["return_code"] == execution["return_code"] == 1
                    assert re.search(r"FAILED \((?:failures|errors)=1\)", transcript)
                    assert expected[-1].split(".")[-1] in transcript
                else:
                    assert one["return_code"] == execution["return_code"] == 0
                    assert re.search(r"(?:^|\n)OK(?:\n|$)", transcript)
                counts[variant] += one["tests"]
        observations.append({"case_id": case["case_id"],
                             "public_commands": len(case["public_commands"]),
                             "buggy_failed_tests": counts["buggy"],
                             "fixed_passed_tests": counts["fixed"],
                             "record_sha256": sha(record_path)})
    return {"status": "TWO_INDEPENDENTLY_AUDITED_PUBLIC_CONTRASTS",
            "lock_sha256": sha(ROOT / "lock.json"),
            "provider_calls": 0, "cases": observations}


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
