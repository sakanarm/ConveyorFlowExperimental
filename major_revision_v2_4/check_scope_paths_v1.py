"""Read-only path check in buggy preflight images; never inspect fixed source."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import preflight_repair_cases_v1 as original
import preflight_repair_cases_v1b as amended


HERE = Path(__file__).resolve().parent
SCOPE = HERE / "source_scope_v1.json"


def main() -> None:
    scopes = json.loads(SCOPE.read_text(encoding="utf-8"))
    rows = []
    for prefix, ledger in ((original.ROOT, original.records()),
                           (amended.ROOT, amended.records())):
        for row in ledger:
            if row["status"] != "reproducible" or row["case_id"] not in scopes:
                continue
            case_root = (prefix / row["case_id"] if prefix == amended.ROOT
                         else prefix / row["project"] / row["case_id"])
            proof = [json.loads(line) for line in (case_root / "engine_ledger.jsonl")
                     .read_text(encoding="utf-8").splitlines() if line.strip()]
            if len(proof) != 1 or proof[0]["selection_hash"] != row["selection_hash"]:
                raise ValueError("Preflight image identity mismatch")
            paths = (scopes[row["case_id"]]["allowed_files"] +
                     scopes[row["case_id"]]["regression_files"])
            program = ("import json,os,sys; paths=json.loads(sys.argv[1]); "
                       "print(json.dumps({p:os.path.isfile('/buggy/'+p) for p in paths}))")
            process = subprocess.run(
                ["podman", "run", "--rm", "--network", "none", "--read-only",
                 proof[0]["container_image_id"], "python", "-B", "-c", program,
                 json.dumps(paths)], capture_output=True, text=True, timeout=120,
                check=False)
            if process.returncode:
                raise RuntimeError(row["case_id"] + " container check failed: " +
                                   process.stderr[-500:])
            exists = json.loads(process.stdout)
            rows.append({"case_id": row["case_id"],
                         "missing_paths": [path for path in paths if not exists[path]]})
    print(json.dumps({"status": "buggy_only_scope_paths_checked",
                      "cases": rows, "provider_calls": 0}))


if __name__ == "__main__":
    main()
