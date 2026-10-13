"""Pre-LLM gold-free candidate and bounded logging regressions for sanic_5.

The public test inventory and per-node stop rule are frozen before outcomes.
Historical v2.5 batch timeout is disclosed; this is a new v2.6 environment and
uses isolated test nodes so one hanging public test cannot consume the batch.
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
sys.path.insert(0, str(HERE))
import build_sanic3_candidate_v1 as helper  # noqa: E402

CASE_ID = "sanic_5"
LOCK_ROOT = HERE / "sanic5_candidate_v1"
LOCK = LOCK_ROOT / "lock.json"
RAW_TEXT = "/mnt/d/ConveyorFlowRuntime/v2_6/sanic5_candidate_v1"
RAW = Path(RAW_TEXT if os.name != "nt" else "D:/ConveyorFlowRuntime/v2_6/sanic5_candidate_v1")
TEST_FILE = "tests/test_logging.py"
MAX_NODES = 3
DOMAIN = "cf-v26-sanic5-public-logging-regressions-20261012"
NODE_TIMEOUT = 120


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path: Path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def case_spec():
    helper.preflight.install()
    state = helper.preflight.q.audit()
    if (state["status"] != "two_cases_qualified" or
            state["qualified_cases"] != ["sanic_5", "sanic_3"]):
        raise ValueError("Frozen v2.6 Sanic preflight not qualified")
    case = helper.preflight.q.read(helper.preflight.q.QUEUE)[0]
    record_path = Path("/mnt/d/ConveyorFlowRuntime/v2_6/sanic_preflight_v1c/00_sanic_5/preflight_record.json")
    record = read(record_path)
    rows = [json.loads(line) for line in helper.preflight.q.LEDGER.read_text(encoding="utf-8").splitlines()]
    if (record["status"] != "reproducible" or record["provider_calls"] != 0 or
            record["selection_hash"] != case["selection_hash"] or
            rows[0]["record_sha256"] != sha(record_path) or
            record["normalized_public_test_node"] !=
            "tests/test_logging.py::test_logging_modified_root_logger_config"):
        raise ValueError("Sanic case 5 preflight evidence drift")
    return {**case, "case_id": CASE_ID,
            "visible_test": record["normalized_public_test_node"],
            "allowed_files": ["sanic/log.py"],
            "validator_source_image": record["container_image_id"],
            "preflight_record_sha256": sha(record_path)}


def freeze():
    case = case_spec()
    stable = {
        "status": "v2_6_sanic5_gold_free_candidate_frozen_before_provider",
        "case": case,
        "public_regression_file": TEST_FILE,
        "regression_selection_rule": "Hash-sort non-visible public test_logging nodes and take first three before outcomes",
        "regression_selection_domain": DOMAIN,
        "minimum_common_active_passes": MAX_NODES,
        "per_node_timeout_seconds": NODE_TIMEOUT,
        "stop_rule": "Stop at first failed or timed-out node pair; retain prior results and do not select replacements",
        "prior_v2_5_failure_disclosed": "Prior Sanic_5 five-node batch public regressions timed out in v2.5; no outcome from that batch is reused or hidden",
        "runner_sha256": sha(Path(__file__)),
        "v2_6_preflight_lock_sha256": sha(helper.preflight.q.LOCK),
        "v2_6_preflight_ledger_sha256": sha(helper.preflight.q.LEDGER),
        "provider_calls": 0,
        "paid_execution_allowed": False,
        "raw_root": RAW_TEXT,
    }
    if LOCK.exists():
        old = read(LOCK)
        if any(old.get(key) != value for key, value in stable.items()):
            raise ValueError("Sanic 5 candidate lock drift")
        return old
    if LOCK_ROOT.exists():
        raise FileExistsError("Partial candidate lock root")
    LOCK_ROOT.mkdir()
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def test_one(image: str, source: str, node: str, output: Path):
    command = (f"cp -a {source} /tmp/work && cd /tmp/work && "
               "PYTHONPATH=/tmp/work python -m pytest -q " + shlex.quote(node) +
               " --junitxml=/reports/tests.xml")
    response, folder = helper.container(image, command, output, timeout=NODE_TIMEOUT)
    xml = folder / "tests.xml"
    return {"return_code": response["return_code"],
            "timeout": bool(response.get("timeout")),
            "counts": helper.test_counts(xml) if xml.exists() else None,
            "dispositions": helper.dispositions(xml) if xml.exists() else {},
            "execution_sha256": sha(output), "xml_sha256": sha(xml) if xml.exists() else None}


def build():
    if sys.platform != "linux" or os.geteuid() != 0 or helper.executable() != "podman":
        raise ValueError("Rootful Linux/Podman required")
    lock = freeze()
    if (shutil.disk_usage("/mnt/c").free < 20 * 1024**3 or
            shutil.disk_usage("/mnt/d").free < 100 * 1024**3):
        raise OSError("Storage stop gate reached")
    if RAW.exists():
        if (RAW / "summary.json").exists():
            return read(RAW / "summary.json")
        raise FileExistsError("Partial candidate attempt retained; audit before retry")
    RAW.mkdir(parents=True)
    case = lock["case"]
    dockerfile = (
        f"FROM {case['validator_source_image']} AS trusted\nUSER root\n"
        "RUN mkdir /candidate /protected && cp -a /buggy/sanic /candidate/ && "
        "find /candidate -type d \\( -name tests -o -name test -o -name __pycache__ \\) -prune -exec rm -rf '{}' + && "
        "find /candidate -name .git -delete\n"
        "RUN cp -a /buggy/. /protected/ && rm -f /protected/.git && "
        "find /protected -type d -name __pycache__ -prune -exec rm -rf '{}' +\n"
        f"FROM {helper.BASE} AS candidate\n"
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
        tag = f"conveyorflow-v26-sanic5-{target}:v1"
        response = helper.execute([helper.executable(), "build", "--target", target, "-t", tag, str(RAW)],
                                  timeout=600, log=RAW / f"{target}_build.json")
        if response["return_code"] != 0 or response.get("timeout"):
            raise RuntimeError("Candidate image build failed; retain raw evidence")
        images[target] = helper.inspect(tag)
    audit = helper.image_audit(images["candidate"], case,
                               RAW / "candidate_audit_execution.json")
    collection = (
        "cp -a /protected /tmp/work && cd /tmp/work && "
        f"PYTHONPATH=/tmp/work python -m pytest --collect-only -q {TEST_FILE}")
    collected, _ = helper.container(images["verifier"], collection,
                                    RAW / "regression_collection.json", timeout=240)
    if collected["return_code"] != 0 or collected.get("timeout"):
        raise RuntimeError("Public logging-test collection failed; raw evidence retained")
    nodes = sorted(set(
        line.strip() for line in collected["stdout"].splitlines()
        if line.startswith(TEST_FILE + "::") and
        line.strip() != case["visible_test"]
    ), key=lambda node: hashlib.sha256((DOMAIN + "|" + CASE_ID + "|" + node).encode()).hexdigest())[:MAX_NODES]
    save_new(RAW / "regression_selection.json", {
        "nodeids": nodes, "frozen_before_regression_outcomes": True,
        "selection_rule": lock["regression_selection_rule"]})
    if len(nodes) < MAX_NODES:
        summary = {"status": "candidate_preflight_failed", "reason": "too_few_public_nodes",
                   "case_id": CASE_ID, "selected_nodes": len(nodes), "provider_calls": 0}
        save_new(RAW / "summary.json", summary)
        return summary
    visible = test_one(images["verifier"], "/protected", case["visible_test"], RAW / "buggy_visible.json")
    pairs = []
    for index, node in enumerate(nodes):
        buggy = test_one(images["verifier"], "/protected", node, RAW / f"buggy_regression_{index}.json")
        fixed = test_one(case["validator_source_image"], "/fixed", node, RAW / f"fixed_regression_{index}.json")
        good = (buggy["return_code"] == fixed["return_code"] == 0 and
                buggy["dispositions"] == fixed["dispositions"] and
                len(buggy["dispositions"]) == 1 and
                set(buggy["dispositions"].values()) == {"passed"} and
                not buggy["timeout"] and not fixed["timeout"])
        pairs.append({"node": node, "buggy": buggy, "fixed": fixed, "common_pass": good})
        if not good:
            break
    passed = (visible["return_code"] == 1 and visible["counts"] is not None and
              visible["counts"]["failures"] > 0 and visible["counts"]["errors"] == 0 and
              not visible["timeout"] and len(pairs) == MAX_NODES and
              all(row["common_pass"] for row in pairs))
    summary = {"status": "candidate_preflight_passed" if passed else "candidate_preflight_failed",
               "case_id": CASE_ID, "candidate_audit": audit, "images": images,
               "public_regression_nodeids": nodes, "visible": visible,
               "regression_pairs": pairs, "lock_sha256": sha(LOCK),
               "provider_calls": 0, "paid_execution_allowed": False,
               "public_tests_not_novel_hidden_tests": True}
    save_new(RAW / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--freeze", action="store_true")
    actions.add_argument("--build", action="store_true")
    args = parser.parse_args()
    result = build() if args.build else freeze()
    print(json.dumps({"status": result["status"], "case_id": CASE_ID,
                      "lock_sha256": sha(LOCK), "provider_calls": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
