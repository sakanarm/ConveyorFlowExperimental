"""Bounded MFEC localized repository repairs with gold-free OCI verification."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from build_bugsinpy_candidate_v1 import container, inspect
from audit_repository_baselines_v2 import dispositions
from repository_patch_guard_v1 import parse_patch

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "real_llm_pilot"
sys.path.insert(0, str(PILOT))
from mfec_adapter import invoke

CONFIG = HERE / "config_repository_repair_pilot_v1.json"
BASE = HERE / "results" / "repository_baseline_gate_v2" / "audit.json"
BUILDS = HERE / "results" / "bugsinpy_candidate_v1"
LOCK = HERE / "repository_repair_pilot_v1_lock.json"
ROOT = HERE / "candidate_workspaces" / "repository_repair_pilot_v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")


def now():
    return datetime.now(timezone.utc).isoformat()


def freeze():
    if not BASE.is_file():
        raise RuntimeError("all six gold-free baseline gates must pass before a provider call")
    baseline = json.loads(BASE.read_text(encoding="utf-8"))
    if baseline["status"] != "baseline_gate_passed":
        raise ValueError("baseline gate failed")
    settings = json.loads(CONFIG.read_text(encoding="utf-8"))
    build = json.loads((BUILDS / "lock.json").read_text(encoding="utf-8"))
    if [c["case_id"] for c in build["cases"]] != settings["case_ids"]:
        raise ValueError("case set drift")
    paths = {"config": CONFIG, "runner": Path(__file__), "baseline_audit": BASE,
             "build_lock": BUILDS / "lock.json", "container_helpers": HERE / "build_bugsinpy_candidate_v1.py",
             "patch_guard": HERE / "repository_patch_guard_v1.py",
             "baseline_disposition_parser": HERE / "audit_repository_baselines_v2.py",
             "provider_config": PILOT / "config.mfec_main_frozen.json",
             "provider_adapter": PILOT / "mfec_adapter.py",
             "credential_bridge": HERE / "wsl_repair_provider_bridge_v1.py"}
    inputs = {name: sha(path) for name, path in paths.items()}
    for case in baseline["cases"]:
        for name in ("summary", "selection"):
            file = BUILDS / case["case_id"] / ("summary.json" if name == "summary" else "regression_selection.json")
            if sha(file) != case[name + "_sha256"]:
                raise ValueError("candidate case evidence drift")
        for image in case["images"].values():
            if inspect(image) != image:
                raise ValueError("locked image is unavailable")
    if LOCK.exists():
        frozen = json.loads(LOCK.read_text(encoding="utf-8"))
        if frozen["inputs"] != inputs:
            raise ValueError("repair protocol inputs changed after freeze")
        return frozen
    frozen = {"status": "frozen_before_repair_provider_calls", "created_at_utc": now(),
              "settings": settings, "inputs": inputs,
              "baseline_audit": baseline, "cases": build["cases"], "research_results": False}
    save(LOCK, frozen)
    return frozen


def make_context(case, baseline, job):
    files = case["allowed_files"]
    # Read source as text from the BUGGY candidate; no imports or fixed tree.
    code = ("import json;from pathlib import Path;"
            f"paths={json.dumps(files)};"
            "print(json.dumps({p:(Path('/candidate')/p).read_text(encoding='utf-8') for p in paths}))")
    raw, _ = container(baseline["images"]["candidate"], "python -c " + shlex.quote(code),
                       job / "context_source_execution.json")
    if raw["return_code"] != 0:
        raise RuntimeError("buggy source context extraction failed")
    sources = json.loads(raw["stdout"])
    visible = json.loads((HERE / case["preflight_artifact"] / "buggy/execution.json").read_text(encoding="utf-8"))
    # Publish only the named visible regression function, not other test bodies.
    test_name = case["visible_test"].split("::")[-1].split("[")[0]
    code = ("import ast,json;from pathlib import Path;"
            f"text=(Path('/protected')/{json.dumps(case['test_file'])}).read_text(encoding='utf-8');"
            f"name={json.dumps(test_name)};"
            "lines=text.splitlines();tree=ast.parse(text);"
            "nodes=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name];"
            "assert len(nodes)==1; n=nodes[0];"
            "print(json.dumps({'visible_test_source':'\\n'.join(lines[n.lineno-1:n.end_lineno])}))")
    test, _ = container(baseline["images"]["verifier"], "python -c " + shlex.quote(code),
                        job / "context_visible_test_execution.json")
    if test["return_code"] != 0:
        raise RuntimeError("visible test context extraction failed")
    return {"case_id": case["case_id"], "buggy_commit": case["buggy_commit_id"],
            "allowed_source_files": sources, "visible_failure": visible["stdout"][-24000:],
            **json.loads(test["stdout"])}


def execute_patch(patch, case, baseline, label, nodes, timeout):
    output = patch.parent / label
    output.mkdir()
    # Mount only the submitted DIFF and the trusted parser. The final verifier
    # image has buggy source/public tests, no fixed production source or history.
    # container() deliberately uses its own timeout cleanup names. Extra mounts
    # are passed by a small wrapper here rather than changing frozen helpers.
    image = baseline["images"]["verifier"]
    name = "cf-repair-" + hashlib.sha256(str(output).encode()).hexdigest()[:20]
    report_dir = output / "reports"
    report_dir.mkdir()
    script = ("set -eu; cp -a /protected /tmp/work; "
              "python /trusted/guard.py " + shlex.quote(json.dumps(case["allowed_files"])) +
              "; cd /tmp/work; PYTHONPATH=/tmp/work:/tmp/work/lib python -m pytest -q " +
              " ".join(shlex.quote(node) for node in nodes) + " --junitxml=/reports/tests.xml")
    command = ["podman", "run", "--name", name, "--rm", "--network", "none", "--read-only",
               "--cpus", "2", "--memory", "4g", "--pids-limit", "256", "--cap-drop", "ALL",
               "--security-opt", "no-new-privileges", "--user", "65534:65534", "--workdir", "/tmp",
               "--tmpfs", "/tmp:rw,nosuid,size=2147483648",
               "--mount", f"type=bind,src={patch.resolve()},dst=/submission/patch.diff,readonly",
               "--mount", f"type=bind,src={(HERE / 'repository_patch_guard_v1.py').resolve()},dst=/trusted/guard.py,readonly",
               "--mount", f"type=bind,src={report_dir.resolve()},dst=/reports",
               image, "sh", "-c", script]
    from run_bugsinpy_preflight import execute, environment
    result = execute(command, timeout=timeout, log=output / "execution.json")
    if result.get("timeout"):
        cleanup = subprocess.run(["podman", "stop", "--time", "5", name], capture_output=True,
                                 text=True, timeout=30, check=False, env=environment())
        save(output / "timeout_cleanup.json", {"name": name, "return_code": cleanup.returncode})
    xml = report_dir / "tests.xml"
    return {"execution": result, "dispositions": dispositions(xml) if xml.is_file() else {},
            "xml_sha256": sha(xml) if xml.is_file() else None}


def run(case_id, slot):
    frozen = freeze()
    settings = frozen["settings"]
    if case_id not in settings["case_ids"] or slot not in settings["model_slots"]:
        raise ValueError("case/model outside bounded pilot")
    case = next(c for c in frozen["cases"] if c["case_id"] == case_id)
    baseline = next(c for c in frozen["baseline_audit"]["cases"] if c["case_id"] == case_id)
    provider = json.loads((PILOT / "config.mfec_main_frozen.json").read_text(encoding="utf-8"))
    model = next(m for m in provider["models"] if m["slot"] == slot)
    ROOT.mkdir(exist_ok=True)
    job = ROOT / (case_id + "_" + slot)
    job.mkdir()  # never rerun/overwrite an existing provider job
    context = make_context(case, baseline, job)
    if sum(len(text) for text in context["allowed_source_files"].values()) > settings["prompt_source_character_cap"]:
        raise ValueError("source context exceeds frozen cap; no provider call")
    save(job / "context.json", context)
    regression = json.loads((BUILDS / case_id / "regression_selection.json").read_text(encoding="utf-8"))["nodeids"]
    known_visible = dispositions(BUILDS / case_id / "candidate_buggy_visible_files" / "tests.xml")
    feedback = None
    attempts = []
    outcome = "DEAD_LETTER"
    for number in range(1, settings["max_attempts_per_job"] + 1):
        directory = job / f"attempt_{number}"
        directory.mkdir()
        prompt = ("Repair the supplied buggy repository source. Return only a JSON object "
                  "with one key patch containing a complete git-style unified diff with exact line "
                  "counts and unchanged context. Modify only the allowed existing Python source files. "
                  "Do not modify tests, configuration, report output, process exit behavior or test "
                  "discovery. Runtime Python is 3.8.20. No network/tools are available. "
                  "The test excerpt and traceback are public visible evidence, not a reference patch.\n" +
                  json.dumps(context, ensure_ascii=False))
        if feedback is not None:
            prompt += "\nPrevious visible-attempt feedback only:\n" + json.dumps(feedback, ensure_ascii=False)
        (directory / "prompt.txt").write_text(prompt, encoding="utf-8")
        request = {"case_id": case_id, "slot": slot, "attempt": number,
                   "started_at_utc": now(), "prompt_sha256": sha(directory / "prompt.txt"),
                   "lock_sha256": sha(LOCK)}
        save(directory / "request_started.json", request)
        print(json.dumps({**request, "status": "provider_request_started"}), flush=True)
        try:
            response = invoke(model={**model, "base_url": provider["base_url"]},
                              case={"prompt": prompt}, generation=settings["generation"])
        except Exception as error:
            save(directory / "provider_error.json", {"type": type(error).__name__,
                 "billable_outcome_unknown": True, "automatic_retry": False})
            attempts.append({**request, "status": "PROVIDER_UNRESOLVED"})
            outcome = "PROVIDER_UNRESOLVED"
            break
        content = str(response.pop("content"))
        (directory / "response.txt").write_text(content, encoding="utf-8")
        save(directory / "provider.json", response)
        if response["exact_model_version"] != model["exact_version"]:
            attempts.append({**request, "status": "PROVIDER_MAPPING_UNRESOLVED"})
            outcome = "PROVIDER_UNRESOLVED"
            break
        record = {**request, "provider_sha256": sha(directory / "provider.json"),
                  "response_sha256": sha(directory / "response.txt")}
        try:
            if response["finish_reason"] != "stop":
                raise ValueError("response did not finish normally within the frozen token cap")
            answer = json.loads(content)
            if set(answer) != {"patch"} or not isinstance(answer["patch"], str):
                raise ValueError("expected exactly the JSON patch schema")
            patch = answer["patch"].encode("utf-8")
            parse_patch(patch, case["allowed_files"])
        except (ValueError, KeyError, TypeError, UnicodeError) as error:
            feedback = {"previous_answer": content[:30000], "visible_error": str(error)}
            record.update(status="PATCH_FORMAT_FAILED", error=str(error))
            save(directory / "attempt_report.json", record)
            attempts.append(record)
            continue
        path = directory / "patch.diff"
        path.write_bytes(patch)
        visible = execute_patch(path, case, baseline, "visible", [case["visible_test"]], settings["execution_timeout_seconds"])
        visible_ok = (visible["execution"]["return_code"] == 0
                      and set(visible["dispositions"]) == set(known_visible)
                      and set(visible["dispositions"].values()) == {"passed"})
        if visible["execution"].get("timeout"):
            record.update(status="EXECUTION_TIMEOUT_UNRESOLVED")
            outcome = "ENVIRONMENT_UNRESOLVED"
        elif not visible_ok:
            record.update(status="VISIBLE_TEST_FAILED")
            feedback = {"previous_patch": answer["patch"], "visible_error": visible["execution"]["stdout"][-16000:]
                        + visible["execution"]["stderr"][-4000:]}
        else:
            checked = execute_patch(path, case, baseline, "regression", regression, settings["execution_timeout_seconds"])
            regression_ok = (checked["execution"]["return_code"] == 0 and
                             checked["dispositions"] == baseline["dispositions"])
            if checked["execution"].get("timeout"):
                record.update(status="REGRESSION_TIMEOUT_UNRESOLVED")
                outcome = "ENVIRONMENT_UNRESOLVED"
            elif not regression_ok:
                record.update(status="WITHHELD_REGRESSION_FAILED")
            else:
                replay_visible = execute_patch(path, case, baseline, "replay_visible", [case["visible_test"]], settings["execution_timeout_seconds"])
                replay_regression = execute_patch(path, case, baseline, "replay_regression", regression, settings["execution_timeout_seconds"])
                replay_ok = (replay_visible["execution"]["return_code"] == replay_regression["execution"]["return_code"] == 0
                             and replay_visible["dispositions"] == visible["dispositions"]
                             and replay_regression["dispositions"] == baseline["dispositions"])
                record.update(status="VERIFIED" if replay_ok else "CLEAN_REPLAY_UNRESOLVED", patch_sha256=sha(path))
                outcome = "VERIFIED" if replay_ok else "ENVIRONMENT_UNRESOLVED"
        save(directory / "attempt_report.json", record)
        attempts.append(record)
        print(json.dumps({"case": case_id, "slot": slot, "attempt": number, "status": record["status"]}), flush=True)
        if outcome in {"VERIFIED", "ENVIRONMENT_UNRESOLVED"} or record["status"] == "WITHHELD_REGRESSION_FAILED":
            break
    summary = {"status": "repository_pilot_completed", "case_id": case_id, "model_slot": slot,
               "model_alias": model["model_id"], "job_outcome": outcome, "attempts": attempts,
               "provider_attempts": len(attempts), "lock_sha256": sha(LOCK), "completed_at_utc": now(),
               "research_results": False, "exploratory_repair_only": True,
               "not_an_allocation_comparison": True, "not_probability_calibration": True,
               "withheld_public_tests_not_novel_hidden_tests": True}
    save(job / "summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--case-id")
    parser.add_argument("--model-slot")
    args = parser.parse_args()
    if args.freeze:
        frozen = freeze()
        print(json.dumps({"status": frozen["status"], "max_provider_calls": frozen["settings"]["max_provider_calls"]}))
    elif args.case_id and args.model_slot:
        print(json.dumps(run(args.case_id, args.model_slot)))
    else:
        parser.error("freeze or provide case and model slot")
