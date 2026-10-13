"""Pre-LLM gold-free and public-regression gate for frozen sanic_3.

This is an eligibility check, not a main Real-LLM result. Case 3 is the second
qualified public-test contrast in the v2.6 Sanic queue. The full historical
fixed tree is used only in a trusted preflight image and never enters the
candidate or verifier images.
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
import preflight_sanic_v1c as preflight  # noqa: E402
from build_bugsinpy_candidate_v1 import container, image_audit, inspect  # noqa: E402
from container_cli import executable  # noqa: E402
from run_bugsinpy_preflight import execute, test_counts  # noqa: E402
from audit_repository_baselines_v2 import dispositions  # noqa: E402

CASE_ID = "sanic_3"
LOCK_ROOT = HERE / "sanic3_candidate_v1"
LOCK = LOCK_ROOT / "lock.json"
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/sanic3_candidate_v1"
RAW = Path(RAW_TEXT if os.name != "nt" else "D:/ConveyorFlowRuntime/v2_6/sanic3_candidate_v1")
BASE = "python:3.8.20-slim-bookworm@sha256:1d52838af602b4b5a831beb13a0e4d073280665ea7be7f69ce2382f29c5a613f"
SETTINGS = {
    "allowed_files": ["sanic/app.py"],
    "public_regression_file": "tests/test_url_for.py",
    "maximum_public_regression_nodes": 5,
    "minimum_active_public_regression_passes": 3,
    "regression_selection_domain": "cf-v26-sanic3-regression-20261011",
    "build_timeout_seconds": 600,
    "test_timeout_seconds": 240,
    "provider_calls": 0,
    "paid_execution_allowed": False,
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def case_spec():
    preflight.install()
    state = preflight.q.audit()
    if (state["status"] != "two_cases_qualified" or
            state["qualified_cases"] != ["sanic_5", "sanic_3"]):
        raise ValueError("Frozen Sanic v2.6 preflight not qualified")
    case = preflight.q.read(preflight.q.QUEUE)[1]
    record_path = Path("/mnt/d/ConveyorFlowRuntime/v2_6/sanic_preflight_v1c/01_sanic_3/preflight_record.json")
    record = read(record_path)
    ledger = [json.loads(line) for line in preflight.q.LEDGER.read_text(encoding="utf-8").splitlines()]
    if (record["status"] != "reproducible" or record["provider_calls"] != 0 or
            record["selection_hash"] != case["selection_hash"] or
            ledger[1]["record_sha256"] != sha(record_path) or
            record["normalized_public_test_node"] != "tests/test_url_for.py::test_routes_with_host"):
        raise ValueError("Sanic case 3 preflight evidence drift")
    return {
        **case,
        "case_id": CASE_ID,
        "visible_test": record["normalized_public_test_node"],
        "allowed_files": SETTINGS["allowed_files"],
        "validator_source_image": record["container_image_id"],
        "preflight_record_sha256": sha(record_path),
    }


def freeze():
    case = case_spec()
    stable = {
        "status": "v2_6_sanic3_gold_free_candidate_frozen_before_provider",
        "case": case,
        "settings": SETTINGS,
        "selection_rule": "Hash-sort public non-visible test_url_for nodes; take first five before outcomes; require three common active passes",
        "runner_sha256": sha(Path(__file__)),
        "preflight_lock_sha256": sha(preflight.q.LOCK),
        "preflight_ledger_sha256": sha(preflight.q.LEDGER),
        "provider_calls": 0,
        "paid_execution_allowed": False,
        "raw_root": RAW_TEXT,
    }
    if LOCK.exists():
        old = read(LOCK)
        if any(old.get(key) != val for key, val in stable.items()):
            raise ValueError("Candidate lock drift")
        return old
    if LOCK_ROOT.exists():
        raise FileExistsError("Partial candidate lock root")
    LOCK_ROOT.mkdir()
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def run_test(image: str, source: str, nodes: list[str], output: Path):
    script = (f"cp -a {source} /tmp/work && cd /tmp/work && "
              "PYTHONPATH=/tmp/work python -m pytest -q " +
              " ".join(shlex.quote(node) for node in nodes) +
              " --junitxml=/reports/tests.xml")
    result, reports = container(image, script, output,
                                timeout=SETTINGS["test_timeout_seconds"])
    xml = reports / "tests.xml"
    return {
        "return_code": result["return_code"],
        "timeout": bool(result.get("timeout")),
        "counts": test_counts(xml) if xml.exists() else None,
        "dispositions": dispositions(xml) if xml.exists() else {},
        "execution_sha256": sha(output),
        "xml_sha256": sha(xml) if xml.exists() else None,
    }


def build():
    if sys.platform != "linux" or os.geteuid() != 0 or executable() != "podman":
        raise ValueError("Rootful Linux/Podman required")
    locked = freeze()
    if shutil.disk_usage("/mnt/c").free < 20 * 1024**3 or shutil.disk_usage("/mnt/d").free < 100 * 1024**3:
        raise OSError("Storage stop gate reached")
    if RAW.exists():
        if (RAW / "summary.json").exists():
            return read(RAW / "summary.json")
        raise FileExistsError("Partial candidate run retained; audit before retry")
    RAW.mkdir(parents=True)
    case = locked["case"]
    dockerfile = (
        f"FROM {case['validator_source_image']} AS trusted\nUSER root\n"
        "RUN mkdir /candidate /protected && cp -a /buggy/sanic /candidate/ && "
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
    (RAW / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    images = {}
    for target in ("candidate", "verifier"):
        tag = f"conveyorflow-v26-sanic3-{target}:v1"
        result = execute([executable(), "build", "--target", target, "-t", tag, str(RAW)],
                         timeout=SETTINGS["build_timeout_seconds"],
                         log=RAW / f"{target}_build.json")
        if result["return_code"] != 0 or result.get("timeout"):
            raise RuntimeError("Candidate image build failed; raw evidence retained")
        images[target] = inspect(tag)
    audit = image_audit(images["candidate"], case, RAW / "candidate_audit_execution.json")
    collect_command = (
        "cp -a /protected /tmp/work && cd /tmp/work && PYTHONPATH=/tmp/work "
        "python -m pytest --collect-only -q tests/test_url_for.py")
    collected, _ = container(images["verifier"], collect_command,
                             RAW / "regression_collection.json",
                             timeout=SETTINGS["test_timeout_seconds"])
    if collected["return_code"] != 0 or collected.get("timeout"):
        raise RuntimeError("Public regression collection failed; evidence retained")
    nodes = sorted(set(
        line.strip() for line in collected["stdout"].splitlines()
        if line.startswith("tests/test_url_for.py::") and
        line.strip() != case["visible_test"]
    ), key=lambda node: hashlib.sha256((
        SETTINGS["regression_selection_domain"] + "|" + CASE_ID + "|" + node
    ).encode()).hexdigest())[:SETTINGS["maximum_public_regression_nodes"]]
    save_new(RAW / "regression_selection.json", {
        "case_id": CASE_ID, "nodeids": nodes,
        "frozen_before_regression_outcomes": True,
        "selection_rule": locked["selection_rule"],
    })
    if len(nodes) < SETTINGS["minimum_active_public_regression_passes"]:
        summary = {"status": "candidate_preflight_failed", "reason": "too_few_public_regressions",
                   "case_id": CASE_ID, "selected_nodes": len(nodes), "provider_calls": 0}
        save_new(RAW / "summary.json", summary)
        return summary
    reports = {
        "buggy_visible": run_test(images["verifier"], "/protected", [case["visible_test"]], RAW / "buggy_visible.json"),
        "buggy_regression": run_test(images["verifier"], "/protected", nodes, RAW / "buggy_regression.json"),
        "fixed_regression": run_test(case["validator_source_image"], "/fixed", nodes, RAW / "fixed_regression.json"),
    }
    visible, buggy, fixed = (reports[key] for key in ("buggy_visible", "buggy_regression", "fixed_regression"))
    active = sum(value == "passed" for value in buggy["dispositions"].values())
    passed = (
        visible["return_code"] == 1 and visible["counts"] is not None and
        visible["counts"]["failures"] > 0 and visible["counts"]["errors"] == 0 and
        buggy["return_code"] == fixed["return_code"] == 0 and
        buggy["dispositions"] == fixed["dispositions"] and
        len(buggy["dispositions"]) == len(nodes) and
        set(buggy["dispositions"].values()) <= {"passed", "expected_failure"} and
        active >= SETTINGS["minimum_active_public_regression_passes"] and
        not any(row["timeout"] for row in reports.values())
    )
    summary = {
        "status": "candidate_preflight_passed" if passed else "candidate_preflight_failed",
        "case_id": CASE_ID, "images": images, "candidate_audit": audit,
        "public_regression_nodeids": nodes, "active_public_regression_passes": active,
        "reports": reports, "lock_sha256": sha(LOCK),
        "dockerfile_sha256": sha(RAW / "Dockerfile"),
        "public_tests_not_novel_hidden_tests": True,
        "provider_calls": 0, "paid_execution_allowed": False,
    }
    save_new(RAW / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--build", action="store_true")
    args = parser.parse_args()
    result = build() if args.build else freeze()
    print(json.dumps({"status": result["status"], "case_id": CASE_ID,
                      "lock_sha256": sha(LOCK), "provider_calls": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
