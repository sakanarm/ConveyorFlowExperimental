from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from run_mfec_calibration import sha256
from run_mfec_fixbug_v2 import load_jsonl, summarize, validate_executable


HERE = Path(__file__).resolve().parent


def latest_corrected_run(root: Path) -> Path:
    runs = sorted(
        (path for path in root.iterdir() if path.is_dir() and (path / "fixbug_v2_corrected_calls.jsonl").exists()),
        reverse=True,
    )
    if not runs:
        raise FileNotFoundError("no corrected Fix Bug v2 run found")
    return runs[0]


def main() -> int:
    root = HERE / "calibration_fixbug_v2_output"
    run = latest_corrected_run(root)
    config = json.loads((HERE / "config.mfec_candidate.json").read_text(encoding="utf-8"))
    probes = {row["probe_id"]: row for row in load_jsonl(HERE / "calibration_fixbug_v2.jsonl")}
    records = load_jsonl(run / "fixbug_v2_corrected_calls.jsonl")
    final_records = []
    for row in records:
        if row["status"] == "success":
            passed, reason, unit_tests = validate_executable(row["response_content"], probes[row["probe_id"]])
            row = {
                **row,
                "passed": passed,
                "validation_reason": reason,
                "unit_tests": unit_tests,
                "finalization": "revalidated_after_safe_parser_false-rejection_correction",
            }
        final_records.append(row)

    ledger = run / "fixbug_v2_final_calls.jsonl"
    with ledger.open("x", encoding="utf-8", newline="\n") as handle:
        for row in final_records:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    summary = summarize(final_records, config["models"])
    summary.update({
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "finalization": (
            "Offline revalidation only: recognize python code fences, allow ordinary underscore loop variables, "
            "and permit safe one-argument type/isinstance checks. No new API calls."
        ),
        "source_corrected_ledger_sha256": sha256(run / "fixbug_v2_corrected_calls.jsonl"),
        "final_ledger_sha256": sha256(ledger),
        "calls": len(final_records),
    })
    (run / "fixbug_v2_final_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
