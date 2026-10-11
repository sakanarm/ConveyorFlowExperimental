"""Read-only independent audit of the Black bug-3 pre-provider candidate gate."""

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/black_candidate_v1"
OUT = ROOT / "black_3"
PREFLIGHT = HERE / "results/black_preflight_v1d/01_black_3/preflight_record.json"
QUEUE = HERE / "results/black_preflight_v1/queue.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition, explanation):
    if not condition:
        raise ValueError(explanation)


def xml_status(path):
    root = ET.parse(path).getroot()
    cases = root.findall(".//testcase")
    dispositions = {}
    for case in cases:
        name = case.attrib["classname"] + "::" + case.attrib["name"]
        check(name not in dispositions, "duplicate JUnit node")
        dispositions[name] = ("failed" if case.find("failure") is not None else
                              "error" if case.find("error") is not None else
                              "skipped" if case.find("skipped") is not None else "passed")
    suite = root.find("testsuite")
    counts = {key: int(suite.attrib[key]) for key in
              ("tests", "failures", "errors", "skipped")}
    check(len(cases) == counts["tests"], "JUnit case count differs")
    return counts, dispositions


def audit():
    lock, summary, preflight = read(ROOT / "lock.json"), read(OUT / "summary.json"), read(PREFLIGHT)
    check(lock["status"] == "v2_5_black3_gold_free_candidate_frozen_before_provider", "lock status")
    check(summary["status"] == "candidate_preflight_passed", "candidate status")
    check(lock["case"]["preflight_record_sha256"] == sha(PREFLIGHT), "preflight hash")
    check(lock["case"]["selection_hash"] == preflight["selection_hash"], "queue selection hash")
    check(preflight["status"] == "reproducible", "bug/fix contrast not qualified")
    check(lock["case"]["validator_source_image"] == preflight["container_image_id"], "source image")
    check(lock["settings"]["allowed_files"] == ["black.py"], "allowed file scope")
    check(summary["candidate_audit"]["blocked_paths"] == [] and
          summary["candidate_audit"]["missing_forbidden_roots"] == [], "candidate leakage audit")
    check(summary["provider_calls"] == lock["provider_calls"] == 0, "provider calls before gate")
    selection = read(OUT / "regression_selection.json")
    nodes = selection["nodeids"]
    check(selection["frozen_before_regression_outcomes"] is True and
          nodes == summary["selected_regression_nodes"] and len(nodes) == 10, "regression selection")
    visible = lock["case"]["visible_test"]
    check(visible not in nodes and len(set(nodes)) == len(nodes), "regression overlap")
    ordering = sorted(nodes, key=lambda node: hashlib.sha256((
        lock["settings"]["selection_domain"] + "|black_3|" + node).encode()).hexdigest())
    check(nodes == ordering, "hash selection ordering")
    expected = {"visible_buggy": (1, "failed", 1), "visible_fixed": (0, "passed", 1),
                "buggy_regressions": (0, "passed", 10),
                "fixed_regressions": (0, "passed", 10)}
    for label, (rc, disposition, count) in expected.items():
        report = summary["reports"][label]
        raw = OUT / (label + ".json")
        xml = OUT / (label + "_files/tests.xml")
        check(sha(raw) == report["execution_sha256"] and
              sha(xml) == report["xml_sha256"], label + " artifact hash")
        counts, actual = xml_status(xml)
        check(counts == report["counts"] and actual == report["dispositions"], label + " JUnit")
        check(report["return_code"] == rc and not report["timeout"] and
              len(actual) == count and set(actual.values()) == {disposition}, label + " outcome")
    check(summary["reports"]["buggy_regressions"]["dispositions"] ==
          summary["reports"]["fixed_regressions"]["dispositions"], "regression asymmetry")
    check(summary["active_regression_passes"] == 10, "active regression count")
    return {"status": "independent_candidate_audit_passed", "case_id": "black_3",
            "independent_repository_replicates_added": 1,
            "public_regression_nodes": 10, "provider_calls": 0,
            "summary_sha256": sha(OUT / "summary.json"), "lock_sha256": sha(ROOT / "lock.json")}


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
