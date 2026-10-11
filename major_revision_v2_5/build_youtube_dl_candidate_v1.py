"""Gold-free youtube-dl bug 27 candidate and public-regression gates.

This script must be frozen and run before any provider sees this case. It
selects regression nodes without using their outcomes or the historical fix.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys

import qualify_youtube_dl_v1b as preflight
from build_black_candidate_v1 import image_audit, inspect, test_run

HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/youtube_dl_candidate_v1"
LOCK = ROOT / "lock.json"
CASE_ID = "youtube-dl_27"
BASE = "python:3.8.20-slim-bookworm@sha256:1d52838af602b4b5a831beb13a0e4d073280665ea7be7f69ce2382f29c5a613f"
SETTINGS = {
    "allowed_files": ["youtube_dl/utils.py"],
    "regression_source": "test/test_utils.py::TestUtil::",
    "maximum_public_regression_nodes": 10,
    "minimum_active_public_regression_passes": 5,
    "selection_domain": "cf-v25-youtube-dl27-public-regression-20261011",
    "build_timeout_seconds": 900,
    "test_timeout_seconds": 240,
    "provider_calls": 0,
    "paid_execution_allowed": False,
}

sys.path.insert(0, str(HERE.parent / "major_revision_v2_3"))
from build_bugsinpy_candidate_v1 import container  # noqa: E402
from container_cli import executable  # noqa: E402
from run_bugsinpy_preflight import execute  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_new(path, data):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")


def case_spec():
    preflight.install()
    status = preflight.q.audit()
    if (status["status"] != "first_case_qualified" or
            status["first_qualified_bug_id"] != "27" or status["attempted"] != 1):
        raise ValueError("First youtube-dl case not reproducibly qualified")
    item = read(preflight.QUEUE)["candidates"][0]
    record_path = preflight.ROOT / "00_youtube_dl_27/preflight_record.json"
    record = read(record_path)
    if (record["status"] != "reproducible" or
            record["selection_hash"] != item["selection_hash"] or
            record["normalized_public_test_node"] !=
            "test/test_utils.py::TestUtil::test_parse_dfxp_time_expr"):
        raise ValueError("Youtube-dl case or public visible test changed")
    for key, relative in (("build_report_sha256", "build_report.json"),
                          ("buggy_test_report_sha256", "buggy/execution.json"),
                          ("fixed_test_report_sha256", "fixed/execution.json")):
        if record[key] != sha(record_path.parent / relative):
            raise ValueError("Preflight artifact changed: " + key)
    return {**item, "case_id": CASE_ID, "project": "youtube-dl",
            "visible_test": record["normalized_public_test_node"],
            "allowed_files": SETTINGS["allowed_files"],
            "validator_source_image": record["container_image_id"],
            "preflight_record_sha256": sha(record_path)}


def freeze():
    case = case_spec()
    stable = {
        "status": "v2_5_youtube_dl27_gold_free_candidate_frozen_before_provider",
        "case": case, "settings": SETTINGS,
        "selection_rule": "Collect public TestUtil nodes; remove visible; hash-sort before outcome; take first ten; require five active common passes and no failures",
        "dependencies_sha256": {
            "runner": sha(__file__),
            "preflight_lock": sha(preflight.LOCK),
            "preflight_ledger": sha(preflight.LEDGER),
            "candidate_helper": sha(HERE.parent / "major_revision_v2_3/build_bugsinpy_candidate_v1.py"),
        },
        "provider_calls": 0, "paid_execution_allowed": False,
    }
    if LOCK.exists():
        locked = read(LOCK)
        if any(locked.get(key) != value for key, value in stable.items()):
            raise ValueError("Youtube-dl candidate lock drift")
        return locked
    if ROOT.exists():
        raise FileExistsError("Candidate root exists without lock")
    ROOT.mkdir(parents=True)
    locked = {**stable, "created_at_utc": datetime.now(timezone.utc).isoformat()}
    save_new(LOCK, locked)
    return locked


def build():
    if sys.platform != "linux" or os.geteuid() != 0 or executable() != "podman":
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
        tag = "conveyorflow-v25-youtube-dl27-" + target + ":v1"
        response = execute([executable(), "build", "--no-cache", "--target", target,
                            "-t", tag, str(out)],
                           timeout=SETTINGS["build_timeout_seconds"],
                           log=out / (target + "_build.json"))
        if response["return_code"] != 0 or response.get("timeout"):
            raise RuntimeError("Youtube-dl candidate image build failed; preserve logs")
        images[target] = inspect(tag)
    audit = image_audit(images["candidate"], case,
                        out / "candidate_audit_execution.json")
    collect = ("cp -a /protected /tmp/work && cd /tmp/work && "
               "PYTHONPATH=/tmp/work python -m pytest --collect-only -q "
               "test/test_utils.py::TestUtil")
    collected, _ = container(images["verifier"], collect,
                             out / "regression_collection.json",
                             timeout=SETTINGS["test_timeout_seconds"])
    if collected["return_code"] != 0 or collected.get("timeout"):
        raise RuntimeError("Youtube-dl public regression collection failed")
    prefix = SETTINGS["regression_source"]
    visible = case["visible_test"]
    nodes = sorted({line.strip() for line in collected["stdout"].splitlines()
                    if line.startswith(prefix) and line.strip() != visible},
                   key=lambda node: hashlib.sha256((SETTINGS["selection_domain"] +
                       "|" + CASE_ID + "|" + node).encode()).hexdigest())
    nodes = nodes[:SETTINGS["maximum_public_regression_nodes"]]
    save_new(out / "regression_selection.json", {
        "case_id": CASE_ID, "nodeids": nodes,
        "frozen_before_regression_outcomes": True,
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
    active = sum(value == "passed" for value in regress["dispositions"].values())
    passed = (bug["return_code"] == 1 and bug["counts"]["failures"] >= 1 and
              bug["counts"]["errors"] == 0 and fixed["return_code"] == 0 and
              regress["return_code"] == control["return_code"] == 0 and
              regress["dispositions"] == control["dispositions"] and
              active >= SETTINGS["minimum_active_public_regression_passes"] and
              not any(item["timeout"] for item in reports.values()))
    summary = {"status": "candidate_preflight_passed" if passed else "candidate_preflight_failed",
               "reason": None if passed else "public_regression_or_visible_gate_failed",
               "case_id": CASE_ID, "images": images,
               "candidate_audit": audit,
               "selected_regression_nodes": nodes,
               "active_regression_passes": active,
               "reports": reports, "provider_calls": 0}
    save_new(out / "summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--build", action="store_true")
    args = parser.parse_args()
    result = build() if args.build else {
        "status": freeze()["status"], "provider_calls": 0}
    print(json.dumps(result, sort_keys=True))
