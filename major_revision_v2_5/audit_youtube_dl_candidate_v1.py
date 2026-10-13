"""Independent, read-only audit of youtube-dl 27 pre-provider gates."""

import hashlib
import json
from pathlib import Path

from audit_black_candidate_v1 import check, read, sha, xml_status

HERE = Path(__file__).resolve().parent
ROOT = HERE / "results/youtube_dl_candidate_v1"
OUT = ROOT / "youtube-dl_27"
PREFLIGHT_ROOT = HERE / "results/youtube_dl_preflight_v1b"
PREFLIGHT = PREFLIGHT_ROOT / "00_youtube_dl_27/preflight_record.json"


def audit():
    lock, summary, preflight = read(ROOT / "lock.json"), read(OUT / "summary.json"), read(PREFLIGHT)
    queue, preflight_lock = read(PREFLIGHT_ROOT / "queue.json"), read(PREFLIGHT_ROOT / "lock.json")
    check(lock["status"] == "v2_5_youtube_dl27_gold_free_candidate_frozen_before_provider",
          "candidate lock status")
    check(preflight_lock["status"] ==
          "v2_5_youtube_dl_preflight_v1b_frozen_no_provider_calls", "preflight lock")
    check(sha(PREFLIGHT_ROOT / "queue.json") == preflight_lock["queue_sha256"] and
          sha(PREFLIGHT_ROOT / "config.json") == preflight_lock["config_sha256"],
          "preflight queue/config drift")
    check(summary["status"] == "candidate_preflight_passed" and
          summary["provider_calls"] == lock["provider_calls"] == 0, "candidate outcome/provider")
    check(lock["case"]["preflight_record_sha256"] == sha(PREFLIGHT) and
          lock["case"]["selection_hash"] == preflight["selection_hash"] ==
          queue["candidates"][0]["selection_hash"], "outcome-blind case selection")
    check(preflight["status"] == "reproducible" and
          lock["case"]["validator_source_image"] == preflight["container_image_id"],
          "bug/fix contrast or source image")
    check(lock["settings"]["allowed_files"] == ["youtube_dl/utils.py"] and
          lock["case"]["visible_test"] ==
          "test/test_utils.py::TestUtil::test_parse_dfxp_time_expr", "file or visible scope")
    candidate = summary["candidate_audit"]
    check(candidate["blocked_paths"] == [] and
          candidate["missing_forbidden_roots"] == [] and
          "youtube_dl/utils.py" in candidate["allowed_source_sha256"],
          "candidate leaks protected or fixed artifacts")
    selection = read(OUT / "regression_selection.json")
    nodes = selection["nodeids"]
    check(selection["frozen_before_regression_outcomes"] is True and
          nodes == summary["selected_regression_nodes"] and len(nodes) == 10 and
          len(set(nodes)) == 10 and lock["case"]["visible_test"] not in nodes,
          "regression selection/overlap")
    ordered = sorted(nodes, key=lambda node: hashlib.sha256((
        lock["settings"]["selection_domain"] + "|youtube-dl_27|" + node
    ).encode()).hexdigest())
    check(nodes == ordered, "regression hash order")
    expected = {"visible_buggy": (1, "failed", 1),
                "visible_fixed": (0, "passed", 1),
                "buggy_regressions": (0, "passed", 10),
                "fixed_regressions": (0, "passed", 10)}
    for label, (rc, disposition, count) in expected.items():
        report = summary["reports"][label]
        raw = OUT / (label + ".json")
        xml = OUT / (label + "_files/tests.xml")
        check(sha(raw) == report["execution_sha256"] and
              sha(xml) == report["xml_sha256"], label + " evidence hash")
        counts, states = xml_status(xml)
        check(counts == report["counts"] and states == report["dispositions"],
              label + " JUnit mismatch")
        check(report["return_code"] == rc and not report["timeout"] and
              len(states) == count and set(states.values()) == {disposition},
              label + " test outcome")
    check(summary["reports"]["buggy_regressions"]["dispositions"] ==
          summary["reports"]["fixed_regressions"]["dispositions"] and
          summary["active_regression_passes"] == 10, "common active regressions")
    return {"status": "independent_candidate_audit_passed",
            "case_id": "youtube-dl_27", "public_regression_nodes": 10,
            "provider_calls": 0,
            "python_environment_deviation": "case 3.7.4, container 3.8.20",
            "summary_sha256": sha(OUT / "summary.json"),
            "lock_sha256": sha(ROOT / "lock.json"),
            "preflight_record_sha256": sha(PREFLIGHT)}


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True))
