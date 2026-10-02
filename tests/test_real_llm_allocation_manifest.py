from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "real_llm_pilot"
sys.path.insert(0, str(PILOT))

from allocation_engine import tasks_from_manifest  # noqa: E402


def test_current_60_case_manifest_converts_to_engine_tasks() -> None:
    with (PILOT / "case_manifest.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))

    tasks = tasks_from_manifest(rows)
    assert len(tasks) == 60
    assert len({task.task_id for task in tasks}) == 60
    assert {task.difficulty for task in tasks} == {1, 2, 3}
