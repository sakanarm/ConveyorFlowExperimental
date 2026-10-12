"""Gold-free candidate and public regression gate for two frozen FastAPI cases.

This pre-LLM gate isolates the buggy fastapi/ package from benchmark tests and
fixed source. Three non-visible public test nodes per case are selected by a
frozen hash rule after full-suite collection but before their outcomes.
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

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(V2 / "major_revision_v2_3"))
sys.path.insert(0, str(V2 / "major_revision_v2_5"))
import preflight_fastapi_multinode_v1c as preflight  # noqa: E402
from build_bugsinpy_candidate_v1 import container, inspect  # noqa: E402
from container_cli import executable  # noqa: E402
from run_bugsinpy_preflight import execute, test_counts  # noqa: E402
from audit_repository_baselines_v2 import dispositions  # noqa: E402

ROOT = HERE / "fastapi_candidates_v1"
LOCK, LEDGER = ROOT / "lock.json", ROOT / "ledger.jsonl"
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/fastapi_candidates_v1"
RAW = Path(RAW_TEXT if os.name != "nt" else
           "D:/ConveyorFlowRuntime/v2_6/fastapi_candidates_v1")
ORDER = ("fastapi_11", "fastapi_8")
BASE = preflight.original.BASE
DOMAIN = "cf-v26-fastapi-public-regressions-20261012"
REGRESSIONS_PER_CASE = 3
BUILD_TIMEOUT = 600
COLLECT_TIMEOUT = 600
TEST_TIMEOUT = 120


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def freeze():
    state = preflight.audit()
    if state["status"] != "two_public_contrasts" or state["qualified_cases"] != list(ORDER):
        raise ValueError("FastAPI two-case public contrast not established")
    queue = read(preflight.original.QUEUE)
    rows = [json.loads(line) for line in preflight.LEDGER.read_text(
        encoding="utf-8").splitlines() if line.strip()]
    cases = []
    for index, case_id in enumerate(ORDER):
        record_path = preflight.RAW / f"{index:02d}_{case_id}/preflight_record.json"
        record = read(record_path)
        if (rows[index]["record_sha256"] != sha(record_path) or
                record["selection_hash"] != queue[index]["selection_hash"] or
                record["status"] != "reproducible" or record["provider_calls"] != 0):
            raise ValueError(f"{case_id} public contrast evidence drift")
        cases.append({"case_id": case_id, "selection_hash": record["selection_hash"],
                      "visible_tests": record["public_test_nodes"],
                      "validator_source_image": record["container_image_id"],
                      "preflight_record_sha256": sha(record_path)})
    stable = {
        "status": "v2_6_fastapi_gold_free_candidates_frozen_before_provider",
        "cases": cases, "candidate_source": "buggy fastapi/ package only",
        "regression_rule": (
            "Collect the public tests/ suite in the buggy verifier; exclude all "
            "visible nodes; hash-sort remaining node IDs by fixed domain/case/node; "
            "take first three before outcomes; require three common active passes "
            "on buggy and fixed, stop at first failing pair without replacement"),
        "selection_domain": DOMAIN,
        "regressions_per_case": REGRESSIONS_PER_CASE,
        "build_timeout_seconds": BUILD_TIMEOUT,
        "collect_timeout_seconds": COLLECT_TIMEOUT,
        "test_timeout_seconds": TEST_TIMEOUT,
        "runner_sha256": sha(Path(__file__)),
        "preflight_lock_sha256": sha(preflight.LOCK),
        "preflight_ledger_sha256": sha(preflight.LEDGER),
        "provider_calls": 0, "paid_execution_allowed": False,
        "raw_root": RAW_TEXT,
    }
    if LOCK.exists():
        old = read(LOCK)
        if any(old.get(key) != value for key, value in stable.items()):
            raise ValueError("FastAPI candidate lock drift")
        return old
    if ROOT.exists():
        raise FileExistsError("Partial FastAPI candidate root")
    ROOT.mkdir()
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def source_map(image: str, root: str, output: Path):
    code = (
        "import hashlib,json;from pathlib import Path;"
        f"r=Path({root!r});"
        "d={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() "
        "for p in r.rglob('*') if p.is_file() and "
        "not {'__pycache__','tests','test','.git'}.intersection(p.parts) "
        "and p.suffix not in {'.pyc','.pyo'}};"
        "print(json.dumps(d,sort_keys=True))"
    )
    result, _ = container(image, "python -c " + shlex.quote(code), output,
                          timeout=TEST_TIMEOUT)
    if result["return_code"] != 0 or result.get("timeout"):
        raise RuntimeError("Source-map audit process failed")
    return json.loads(result["stdout"])


def candidate_audit(candidate: str, source: str, output: Path):
    code = (
        "import json;from pathlib import Path;"
        "r=Path('/candidate');"
        "print(json.dumps({'forbidden_roots':[p for p in "
        "['/buggy','/fixed','/protected','/source'] if Path(p).exists()],"
        "'forbidden_paths':[str(p) for p in r.rglob('*') if "
        "p.name in {'tests','test','.git','bug_patch.txt','gold.patch'}],"
        "'installed_fastapi':any(Path(p).exists() for p in "
        "['/usr/local/lib/python3.8/site-packages/fastapi',"
        "'/usr/local/lib/python3.8/site-packages/fastapi.py'])}))"
    )
    result, _ = container(candidate, "python -c " + shlex.quote(code), output,
                          timeout=TEST_TIMEOUT)
    if result["return_code"] != 0 or result.get("timeout"):
        raise RuntimeError("Gold-free image audit failed")
    checks = json.loads(result["stdout"])
    if (checks["forbidden_roots"] or checks["forbidden_paths"] or
            checks["installed_fastapi"]):
        raise ValueError("Candidate image contains protected material")
    candidate_files = source_map(candidate, "/candidate/fastapi",
                                 output.with_name("candidate_source_hashes.json"))
    buggy_files = source_map(source, "/buggy/fastapi",
                             output.with_name("buggy_source_hashes.json"))
    if not candidate_files or candidate_files != buggy_files:
        raise ValueError("Candidate package differs from buggy source")
    return {"source_files": len(candidate_files), "forbidden_roots": [],
            "forbidden_paths": [], "installed_fastapi": False,
            "candidate_source_map_sha256": sha(output.with_name("candidate_source_hashes.json")),
            "buggy_source_map_sha256": sha(output.with_name("buggy_source_hashes.json"))}


def test_one(image: str, source: str, node: str, output: Path):
    script = (f"cp -a {source} /tmp/work && cd /tmp/work && "
              "PYTHONPATH=/tmp/work python -m pytest -q " + shlex.quote(node) +
              " --junitxml=/reports/tests.xml")
    result, files = container(image, script, output, timeout=TEST_TIMEOUT)
    xml = files / "tests.xml"
    return {"return_code": result["return_code"],
            "timeout": bool(result.get("timeout")),
            "counts": test_counts(xml) if xml.exists() else None,
            "dispositions": dispositions(xml) if xml.exists() else {},
            "execution_sha256": sha(output),
            "xml_sha256": sha(xml) if xml.exists() else None}


def audit():
    freeze()
    rows = [json.loads(line) for line in LEDGER.read_text(
        encoding="utf-8").splitlines() if line.strip()] if LEDGER.exists() else []
    if len(rows) > len(ORDER):
        raise ValueError("Too many FastAPI candidate attempts")
    for index, row in enumerate(rows):
        summary = RAW / f"{index:02d}_{ORDER[index]}/summary.json"
        if (row["queue_index"] != index or row["case_id"] != ORDER[index] or
                row["summary_sha256"] != sha(summary) or row["provider_calls"] != 0):
            raise ValueError("FastAPI candidate ledger/evidence drift")
    passed = [row["case_id"] for row in rows if row["status"] == "candidate_preflight_passed"]
    return {"status": "two_candidate_gate_passes_not_independently_audited"
            if len(passed) == 2 else "project_ineligible" if any(
                row["status"] == "candidate_preflight_failed" for row in rows) else
            "candidate_preflight_incomplete",
            "attempted": len(rows), "qualified_cases": passed,
            "provider_calls": 0, "lock_sha256": sha(LOCK)}


def run_next():
    if sys.platform != "linux" or os.geteuid() != 0 or executable() != "podman":
        raise ValueError("Rootful Linux/Podman required")
    state = audit()
    if state["status"] != "candidate_preflight_incomplete":
        return state
    if (shutil.disk_usage("/mnt/c").free < 20 * 1024**3 or
            shutil.disk_usage("/mnt/d").free < 100 * 1024**3):
        raise OSError("Storage stop gate reached")
    index = state["attempted"]
    case = read(LOCK)["cases"][index]
    out = RAW / f"{index:02d}_{case['case_id']}"
    if out.exists():
        raise FileExistsError("Partial candidate attempt retained; audit before retry")
    out.mkdir(parents=True)
    dockerfile = (
        f"FROM {case['validator_source_image']} AS trusted\nUSER root\n"
        "RUN mkdir /candidate /protected && cp -a /buggy/fastapi /candidate/ && "
        "find /candidate -type d \\( -name tests -o -name test -o -name __pycache__ \\) "
        "-prune -exec rm -rf '{}' + && find /candidate -name .git -delete\n"
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
        tag = f"conveyorflow-v26-{case['case_id']}-{target}:candidate-v1"
        result = execute([executable(), "build", "--target", target, "-t", tag, str(out)],
                         timeout=BUILD_TIMEOUT, log=out / f"{target}_build.json")
        if result["return_code"] != 0 or result.get("timeout"):
            raise RuntimeError("Candidate image build failed; raw evidence retained")
        images[target] = inspect(tag)
    source_check = candidate_audit(images["candidate"], case["validator_source_image"],
                                   out / "candidate_audit_execution.json")
    collected, _ = container(
        images["verifier"],
        "cp -a /protected /tmp/work && cd /tmp/work && "
        "PYTHONPATH=/tmp/work python -m pytest --collect-only -q tests",
        out / "regression_collection.json", timeout=COLLECT_TIMEOUT)
    if collected["return_code"] != 0 or collected.get("timeout"):
        raise RuntimeError("Public suite collection failed; raw evidence retained")
    nodes = sorted(set(
        line.strip() for line in collected["stdout"].splitlines()
        if line.startswith("tests/") and "::" in line and
        line.strip() not in case["visible_tests"] and
        not any(line.strip().startswith(visible + "[")
                for visible in case["visible_tests"])
    ), key=lambda node: hashlib.sha256((
        DOMAIN + "|" + case["case_id"] + "|" + node).encode()).hexdigest())
    nodes = nodes[:REGRESSIONS_PER_CASE]
    save_new(out / "regression_selection.json", {
        "nodeids": nodes, "frozen_before_regression_outcomes": True,
        "selection_rule": read(LOCK)["regression_rule"]})
    if len(nodes) < REGRESSIONS_PER_CASE:
        summary = {"status": "candidate_preflight_failed", "reason": "too_few_public_nodes",
                   "case_id": case["case_id"], "selected_nodes": len(nodes),
                   "provider_calls": 0}
    else:
        visible = [test_one(images["verifier"], "/protected", node,
                            out / f"buggy_visible_{number}.json")
                   for number, node in enumerate(case["visible_tests"])]
        pairs = []
        for node_index, node in enumerate(nodes):
            buggy = test_one(images["verifier"], "/protected", node,
                             out / f"buggy_regression_{node_index}.json")
            fixed = test_one(case["validator_source_image"], "/fixed", node,
                             out / f"fixed_regression_{node_index}.json")
            common_pass = (buggy["return_code"] == fixed["return_code"] == 0 and
                           not buggy["timeout"] and not fixed["timeout"] and
                           buggy["dispositions"] == fixed["dispositions"] and
                           len(buggy["dispositions"]) == 1 and
                           set(buggy["dispositions"].values()) == {"passed"})
            pairs.append({"node": node, "buggy": buggy, "fixed": fixed,
                          "common_pass": common_pass})
            if not common_pass:
                break
        visible_ok = all(
            row["return_code"] != 0 and row["counts"] is not None and
            row["counts"]["failures"] > 0 and
            row["counts"]["errors"] == row["counts"]["skipped"] == 0 and
            not row["timeout"] for row in visible)
        passed = (visible_ok and len(pairs) == REGRESSIONS_PER_CASE and
                  all(pair["common_pass"] for pair in pairs))
        summary = {"status": "candidate_preflight_passed" if passed else
                   "candidate_preflight_failed", "case_id": case["case_id"],
                   "candidate_audit": source_check, "images": images,
                   "public_regression_nodeids": nodes, "visible": visible,
                   "regression_pairs": pairs, "provider_calls": 0,
                   "public_tests_not_novel_hidden_tests": True}
    save_new(out / "summary.json", summary)
    row = {"queue_index": index, "case_id": case["case_id"],
           "status": summary["status"], "summary_sha256": sha(out / "summary.json"),
           "provider_calls": 0}
    with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--freeze", action="store_true")
    modes.add_argument("--audit", action="store_true")
    modes.add_argument("--run-next", action="store_true")
    args = parser.parse_args()
    result = run_next() if args.run_next else audit() if args.audit else freeze()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
