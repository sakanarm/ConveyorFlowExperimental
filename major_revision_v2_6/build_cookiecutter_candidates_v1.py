"""Pre-LLM, gold-free Cookiecutter candidate and public-regression gates.

Two cases are taken in the frozen preflight order. Only the buggy package is
copied into the agent-facing image; the verifier receives the buggy test tree.
The historical fixed tree stays in the trusted source image for validation.
All selection rules are locked before regression outcomes are observed.
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

import preflight_cookiecutter_v1d as preflight  # noqa: E402
from build_bugsinpy_candidate_v1 import container, inspect  # noqa: E402
from container_cli import executable  # noqa: E402
from run_bugsinpy_preflight import execute, test_counts  # noqa: E402
from audit_repository_baselines_v2 import dispositions  # noqa: E402

ROOT = HERE / "cookiecutter_candidates_v1"
LOCK = ROOT / "lock.json"
LEDGER = ROOT / "ledger.jsonl"
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/cookiecutter_candidates_v1"
RAW = Path(RAW_TEXT if os.name != "nt" else
           "D:/ConveyorFlowRuntime/v2_6/cookiecutter_candidates_v1")
BASE = preflight.original.BASE
ORDER = ("cookiecutter_3", "cookiecutter_1")
DOMAIN = "cf-v26-cookiecutter-public-regressions-20261012"
REGRESSIONS_PER_CASE = 3
NODE_TIMEOUT_SECONDS = 120
BUILD_TIMEOUT_SECONDS = 600


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
        raise ValueError("Cookiecutter public contrast gate is not frozen/passed")
    source = read(preflight.QUEUE)
    rows = [json.loads(line) for line in preflight.LEDGER.read_text(
        encoding="utf-8").splitlines() if line.strip()]
    cases = []
    for index, case_id in enumerate(ORDER):
        record_path = preflight.RAW / f"{index:02d}_{case_id}/preflight_record.json"
        record = read(record_path)
        if (rows[index]["record_sha256"] != sha(record_path) or
                record["selection_hash"] != source[index]["selection_hash"] or
                record["status"] != "reproducible" or record["provider_calls"] != 0):
            raise ValueError(f"{case_id} preflight evidence drift")
        cases.append({"case_id": case_id, "selection_hash": record["selection_hash"],
                      "visible_test": record["normalized_public_test_node"],
                      "public_test_file": source[index]["test_file"],
                      "validator_source_image": record["container_image_id"],
                      "preflight_record_sha256": sha(record_path)})
    stable = {
        "status": "v2_6_cookiecutter_gold_free_candidates_frozen_before_provider",
        "cases": cases, "candidate_source": "buggy cookiecutter/ package only",
        "regression_rule": (
            "Collect non-visible nodes from each case's public test file; "
            "hash-sort by fixed domain/case/node and take first three before outcomes; "
            "run individually and require three common active passes; "
            "stop at first failed pair without replacement"),
        "selection_domain": DOMAIN,
        "regressions_per_case": REGRESSIONS_PER_CASE,
        "node_timeout_seconds": NODE_TIMEOUT_SECONDS,
        "build_timeout_seconds": BUILD_TIMEOUT_SECONDS,
        "runner_sha256": sha(Path(__file__)),
        "preflight_lock_sha256": sha(preflight.LOCK),
        "preflight_ledger_sha256": sha(preflight.LEDGER),
        "provider_calls": 0, "paid_execution_allowed": False,
        "raw_root": RAW_TEXT,
    }
    if LOCK.exists():
        old = read(LOCK)
        if any(old.get(key) != value for key, value in stable.items()):
            raise ValueError("Cookiecutter candidate lock drift")
        return old
    if ROOT.exists():
        raise FileExistsError("Partial Cookiecutter candidate root")
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
                          timeout=NODE_TIMEOUT_SECONDS)
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
        "p.name in {'tests','test','.git','bug_patch.txt','gold.patch'}]}))"
    )
    result, _ = container(candidate, "python -c " + shlex.quote(code), output,
                          timeout=NODE_TIMEOUT_SECONDS)
    if result["return_code"] != 0 or result.get("timeout"):
        raise RuntimeError("Gold-free image audit failed")
    checks = json.loads(result["stdout"])
    if checks["forbidden_roots"] or checks["forbidden_paths"]:
        raise ValueError("Candidate image contains protected material")
    candidate_files = source_map(candidate, "/candidate/cookiecutter",
                                 output.with_name("candidate_source_hashes.json"))
    buggy_files = source_map(source, "/buggy/cookiecutter",
                             output.with_name("buggy_source_hashes.json"))
    if not candidate_files or candidate_files != buggy_files:
        raise ValueError("Candidate package differs from buggy source")
    return {"source_files": len(candidate_files),
            "candidate_source_map_sha256": sha(output.with_name("candidate_source_hashes.json")),
            "buggy_source_map_sha256": sha(output.with_name("buggy_source_hashes.json")),
            "forbidden_roots": [], "forbidden_paths": []}


def test_one(image: str, source: str, node: str, output: Path):
    script = (f"cp -a {source} /tmp/work && cd /tmp/work && "
              "PYTHONPATH=/tmp/work python -m pytest -q " + shlex.quote(node) +
              " --junitxml=/reports/tests.xml")
    result, files = container(image, script, output,
                              timeout=NODE_TIMEOUT_SECONDS)
    xml = files / "tests.xml"
    return {"return_code": result["return_code"],
            "timeout": bool(result.get("timeout")),
            "counts": test_counts(xml) if xml.exists() else None,
            "dispositions": dispositions(xml) if xml.exists() else {},
            "execution_sha256": sha(output),
            "xml_sha256": sha(xml) if xml.exists() else None}


def audit():
    lock = freeze()
    rows = [json.loads(line) for line in LEDGER.read_text(
        encoding="utf-8").splitlines() if line.strip()] if LEDGER.exists() else []
    if len(rows) > len(ORDER):
        raise ValueError("Too many candidate attempts")
    for index, row in enumerate(rows):
        case_id = ORDER[index]
        summary = RAW / f"{index:02d}_{case_id}/summary.json"
        if (row["queue_index"] != index or row["case_id"] != case_id or
                row["summary_sha256"] != sha(summary) or
                row["provider_calls"] != 0):
            raise ValueError("Candidate ledger/evidence drift")
    passed = [row["case_id"] for row in rows if row["status"] == "candidate_preflight_passed"]
    return {"status": "two_candidates_qualified" if len(passed) == 2 else
            "project_ineligible" if len(rows) == 2 else "candidate_preflight_incomplete",
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
        "RUN mkdir /candidate /protected && cp -a /buggy/cookiecutter /candidate/ && "
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
                         timeout=BUILD_TIMEOUT_SECONDS, log=out / f"{target}_build.json")
        if result["return_code"] != 0 or result.get("timeout"):
            raise RuntimeError("Candidate image build failed; raw evidence retained")
        images[target] = inspect(tag)
    source_check = candidate_audit(images["candidate"], case["validator_source_image"],
                                   out / "candidate_audit_execution.json")
    collected, _ = container(
        images["verifier"],
        "cp -a /protected /tmp/work && cd /tmp/work && "
        "PYTHONPATH=/tmp/work python -m pytest --collect-only -q " +
        shlex.quote(case["public_test_file"]),
        out / "regression_collection.json", timeout=240)
    if collected["return_code"] != 0 or collected.get("timeout"):
        raise RuntimeError("Public regression collection failed; raw evidence retained")
    nodes = sorted(set(
        line.strip() for line in collected["stdout"].splitlines()
        if line.startswith(case["public_test_file"] + "::") and
        line.strip() != case["visible_test"] and
        not line.strip().startswith(case["visible_test"] + "[")
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
        visible = test_one(images["verifier"], "/protected", case["visible_test"],
                           out / "buggy_visible.json")
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
        passed = (visible["return_code"] != 0 and visible["counts"] is not None and
                  visible["counts"]["failures"] > 0 and
                  visible["counts"]["errors"] == visible["counts"]["skipped"] == 0 and
                  not visible["timeout"] and len(pairs) == REGRESSIONS_PER_CASE and
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
