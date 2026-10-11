"""Gold-free candidate/verifier images and public regressions for Black bug 3.

The source case was selected by the original frozen Black queue. The only
allowed repair path is black.py, the module reached by the visible failure.
Neither the candidate image nor the prompt contains the historical fixed tree.
"""

from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys

import qualify_black_v1 as cohort
import qualify_black_v1d as preflight

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "major_revision_v2_3"
sys.path.insert(0, str(OLD))
from audit_repository_baselines_v2 import dispositions  # noqa: E402
from build_bugsinpy_candidate_v1 import container, image_audit, inspect  # noqa: E402
from container_cli import executable  # noqa: E402
from run_bugsinpy_preflight import execute, test_counts  # noqa: E402


ROOT = HERE / "results/black_candidate_v1"
LOCK = ROOT / "lock.json"
CASE_ID = "black_3"
BASE = "python:3.8.20-slim-bookworm@sha256:1d52838af602b4b5a831beb13a0e4d073280665ea7be7f69ce2382f29c5a613f"
SETTINGS = {
    "allowed_files": ["black.py"],
    "regression_source": "tests/test_black.py::BlackTestCase::",
    "maximum_public_regression_nodes": 10,
    "minimum_active_public_regression_passes": 5,
    "selection_domain": "cf-v25-black3-public-regression-20261011",
    "build_timeout_seconds": 900,
    "test_timeout_seconds": 240,
    "provider_calls": 0,
    "paid_execution_allowed": False,
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def case_spec() -> dict:
    audited = preflight.audit()
    if (audited["status"] != "first_case_qualified" or
            audited["first_qualified_bug_id"] != "3" or audited["attempted"] != 2):
        raise ValueError("Original-order Black qualification incomplete")
    item = read(cohort.QUEUE)["candidates"][1]
    path = preflight.ROOT / "01_black_3/preflight_record.json"
    record = read(path)
    if (record["status"] != "reproducible" or
            record["selection_hash"] != item["selection_hash"] or
            record["normalized_public_test_node"] !=
            "tests/test_black.py::BlackTestCase::test_invalid_config_return_code"):
        raise ValueError("Selected public bug contrast drift")
    for key, relative in (("build_report_sha256", "build_report.json"),
                          ("buggy_test_report_sha256", "buggy/execution.json"),
                          ("fixed_test_report_sha256", "fixed/execution.json")):
        if record[key] != sha(path.parent / relative):
            raise ValueError("Preflight artifact changed: " + key)
    return {**item, "case_id": CASE_ID, "project": "black",
            "visible_test": record["normalized_public_test_node"],
            "allowed_files": SETTINGS["allowed_files"],
            "validator_source_image": record["container_image_id"],
            "preflight_record_sha256": sha(path)}


def freeze() -> dict:
    stable = {
        "status": "v2_5_black3_gold_free_candidate_frozen_before_provider",
        "case": case_spec(), "settings": SETTINGS,
        "selection_rule": "Collect BlackTestCase public nodes, remove visible bug node, hash-sort and take first ten before regression outcomes; require at least five active common passes and no failures",
        "dependencies_sha256": {
            "runner": sha(Path(__file__)),
            "cohort_queue": sha(cohort.QUEUE),
            "preflight_lock": sha(preflight.LOCK),
            "preflight_ledger": sha(preflight.LEDGER),
            "candidate_helper": sha(OLD / "build_bugsinpy_candidate_v1.py"),
        },
        "provider_calls": 0, "paid_execution_allowed": False,
    }
    if LOCK.exists():
        locked = read(LOCK)
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError("Black candidate lock drift")
        return locked
    if ROOT.exists():
        raise FileExistsError("Black candidate root exists without lock")
    ROOT.mkdir(parents=True)
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def test_run(image: str, source: str, nodes: list[str], output: Path) -> dict:
    script = (f"cp -a {source} /tmp/work && cd /tmp/work && "
              "PYTHONPATH=/tmp/work python -m pytest -q " +
              " ".join(shlex.quote(node) for node in nodes) +
              " --junitxml=/reports/tests.xml")
    execution, reports = container(image, script, output,
                                   timeout=SETTINGS["test_timeout_seconds"])
    xml = reports / "tests.xml"
    return {"return_code": execution["return_code"],
            "timeout": bool(execution.get("timeout")),
            "counts": test_counts(xml) if xml.exists() else None,
            "dispositions": dispositions(xml) if xml.exists() else {},
            "execution_sha256": sha(output),
            "xml_sha256": sha(xml) if xml.exists() else None}


def build() -> dict:
    if (sys.platform != "linux" or os.geteuid() != 0 or
            executable() != "podman"):
        raise ValueError("Rootful Linux/Podman required")
    locked = freeze()
    out = ROOT / CASE_ID
    if out.exists():
        if (out / "summary.json").exists():
            return read(out / "summary.json")
        raise FileExistsError("Interrupted candidate build retained")
    out.mkdir()
    case = locked["case"]
    dockerfile = (
        f"FROM {case['validator_source_image']} AS trusted\nUSER root\n"
        "RUN mkdir /candidate /protected && cp -a /buggy/. /candidate/ && "
        "find /candidate -type d \\( -name tests -o -name test -o -name __pycache__ \\) -prune -exec rm -rf '{}' + && "
        "rm -f /candidate/.git /candidate/bug_patch.txt\n"
        "RUN cp -a /buggy/. /protected/ && rm -f /protected/.git\n"
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
        tag = f"conveyorflow-v25-black3-{target}:v1"
        response = execute([executable(), "build", "--no-cache", "--target", target,
                            "-t", tag, str(out)], timeout=SETTINGS["build_timeout_seconds"],
                           log=out / f"{target}_build.json")
        if response["return_code"] != 0 or response.get("timeout"):
            raise RuntimeError("Black candidate image build failed; preserve logs")
        images[target] = inspect(tag)
    audit = image_audit(images["candidate"], case, out / "candidate_audit_execution.json")
    collect = ("cp -a /protected /tmp/work && cd /tmp/work && "
               "PYTHONPATH=/tmp/work python -m pytest --collect-only -q "
               "tests/test_black.py::BlackTestCase")
    collected, _ = container(images["verifier"], collect,
                             out / "regression_collection.json",
                             timeout=SETTINGS["test_timeout_seconds"])
    if collected["return_code"] != 0 or collected.get("timeout"):
        raise RuntimeError("Black public regression collection failed")
    prefix = SETTINGS["regression_source"]
    visible = case["visible_test"]
    nodes = sorted({line.strip() for line in collected["stdout"].splitlines()
                    if line.startswith(prefix) and line.strip() != visible},
                   key=lambda node: hashlib.sha256((SETTINGS["selection_domain"] +
                       "|" + CASE_ID + "|" + node).encode()).hexdigest())
    nodes = nodes[:SETTINGS["maximum_public_regression_nodes"]]
    save_new(out / "regression_selection.json", {"case_id": CASE_ID,
             "nodeids": nodes, "frozen_before_regression_outcomes": True,
             "selection_rule": locked["selection_rule"]})
    if len(nodes) < SETTINGS["minimum_active_public_regression_passes"]:
        summary = {"status": "candidate_preflight_failed",
                   "reason": "too_few_public_regressions", "selected": len(nodes),
                   "case_id": CASE_ID, "images": images, "candidate_audit": audit,
                   "provider_calls": 0}
        save_new(out / "summary.json", summary)
        return summary
    reports = {
        "visible_buggy": test_run(images["verifier"], "/protected", [visible],
                                  out / "visible_buggy.json"),
        "visible_fixed": test_run(case["validator_source_image"], "/fixed", [visible],
                                  out / "visible_fixed.json"),
        "buggy_regressions": test_run(images["verifier"], "/protected", nodes,
                                      out / "buggy_regressions.json"),
        "fixed_regressions": test_run(case["validator_source_image"], "/fixed", nodes,
                                      out / "fixed_regressions.json"),
    }
    bug, fixed = reports["visible_buggy"], reports["visible_fixed"]
    regress, control = reports["buggy_regressions"], reports["fixed_regressions"]
    active = sum(outcome == "passed" for outcome in regress["dispositions"].values())
    passed = (bug["return_code"] == 1 and bug["counts"]["failures"] >= 1 and
              bug["counts"]["errors"] == 0 and fixed["return_code"] == 0 and
              regress["return_code"] == control["return_code"] == 0 and
              regress["dispositions"] == control["dispositions"] and
              active >= SETTINGS["minimum_active_public_regression_passes"] and
              not any(item["timeout"] for item in reports.values()))
    summary = {"status": "candidate_preflight_passed" if passed else "candidate_preflight_failed",
               "reason": None if passed else "public_regression_or_visible_gate_failed",
               "case_id": CASE_ID, "images": images, "candidate_audit": audit,
               "selected_regression_nodes": nodes, "active_regression_passes": active,
               "reports": reports, "provider_calls": 0}
    save_new(out / "summary.json", summary)
    return summary


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    action = cli.add_mutually_exclusive_group(required=True)
    action.add_argument("--freeze", action="store_true")
    action.add_argument("--build", action="store_true")
    args = cli.parse_args()
    result = build() if args.build else {"status": freeze()["status"], "provider_calls": 0}
    print(json.dumps(result, sort_keys=True))
