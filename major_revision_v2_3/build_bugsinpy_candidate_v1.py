"""Construct six gold-free candidate/verifier images before any LLM call.

Only trusted benchmark metadata and hash-audited preflight images are read.
Repository imports/tests run in isolated OCI containers, never on the host.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from container_cli import canonical_image_id, executable
from run_bugsinpy_preflight import environment, execute, test_counts
from select_bugsinpy_pilot import MANIFEST, select

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config_bugsinpy_candidate_v1.json"
OUT = HERE / "results" / "bugsinpy_candidate_v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, data):
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(data, indent=2) + "\n")


def inspect(image):
    result = subprocess.run([executable(), "image", "inspect", image, "--format", "{{.Id}}"],
                            capture_output=True, text=True, timeout=30, check=True,
                            env=environment())
    return canonical_image_id(result.stdout)


def container(image, script, output, timeout=180):
    # A unique name permits exact cleanup after host-side timeout.
    name = "cf-bip-candidate-" + hashlib.sha256(str(output).encode()).hexdigest()[:20]
    reports = output.parent / (output.stem + "_files")
    reports.mkdir()
    result = execute([
        executable(), "run", "--name", name, "--rm", "--network", "none", "--read-only",
        "--cpus", "2", "--memory", "4g", "--pids-limit", "256",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", "65534:65534", "--workdir", "/tmp",
        "--tmpfs", "/tmp:rw,nosuid,size=2147483648",
        "--mount", f"type=bind,src={reports.resolve()},dst=/reports",
        image, "sh", "-c", script,
    ], timeout=timeout, log=output)
    if result.get("timeout"):
        cleanup = subprocess.run([executable(), "stop", "--time", "5", name],
                                 capture_output=True, text=True, timeout=30,
                                 check=False, env=environment())
        write_new(output.with_name(output.stem + "_timeout_cleanup.json"),
                  {"name": name, "return_code": cleanup.returncode,
                   "stdout": cleanup.stdout[-1000:], "stderr": cleanup.stderr[-1000:]})
    return result, reports


def freeze():
    settings = json.loads(CONFIG.read_text(encoding="utf-8"))
    ledger = HERE / settings["selection_ledger"]
    selection = select(MANIFEST, ledger)
    if len(selection["selected"]) != 6:
        raise RuntimeError("six-case, three-repository selection is not complete")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    cases = []
    for chosen in selection["selected"]:
        item = next(x for x in manifest["candidates"] if x["selection_hash"] == chosen["selection_hash"])
        record = next(x for x in records if x["selection_hash"] == chosen["selection_hash"])
        artifact = HERE / record["artifact_directory"]
        # Selector validates schema; here audit hashes against actual files too.
        for field, relative in (("buggy_test_report_sha256", "buggy/execution.json"),
                                ("fixed_test_report_sha256", "fixed/execution.json"),
                                ("dockerfile_sha256", "Dockerfile"),
                                ("build_report_sha256", "build_report.json")):
            if sha(artifact / relative) != record[field]:
                raise ValueError("source preflight artifact changed")
        if inspect(record["container_image_id"]) != record["container_image_id"]:
            raise ValueError("source preflight image unavailable")
        metadata = HERE.parent / "bip" / "projects" / item["project"] / "bugs" / item["bug_id"]
        visible = shlex.split((metadata / "run_test.sh").read_text(encoding="utf-8").strip())[1]
        case_id = item["project"] + "_" + item["bug_id"]
        cases.append({**item, "case_id": case_id,
                      "validator_source_image": record["container_image_id"],
                      "visible_test": visible,
                      "allowed_files": settings["allowed_files"][case_id],
                      "preflight_artifact": record["artifact_directory"],
                      "environment_deviation": record["environment_deviation"]})
    frozen = {"created_at_utc": datetime.now(timezone.utc).isoformat(),
              "status": "frozen_before_candidate_build_and_llm", "no_llm_calls": True,
              "config_sha256": sha(CONFIG), "runner_sha256": sha(Path(__file__)),
              "preflight_runner_sha256": sha(HERE / "run_bugsinpy_preflight.py"),
              "selection": selection, "settings": settings, "cases": cases}
    lock = OUT / "lock.json"
    OUT.mkdir(exist_ok=True)
    if lock.exists():
        previous = json.loads(lock.read_text(encoding="utf-8"))
        for field in ("config_sha256", "runner_sha256", "preflight_runner_sha256", "selection", "settings", "cases"):
            if previous[field] != frozen[field]:
                raise ValueError("candidate protocol changed after freeze")
        return previous
    write_new(lock, frozen)
    return frozen


def image_audit(image, case, output):
    allowed = json.dumps(case["allowed_files"])
    code = (
        "import hashlib,json;from pathlib import Path;"
        "r=Path('/candidate');"
        "blocked=[str(p) for p in r.rglob('*') if p.name in "
        "{'.git','tests','test','bug_patch.txt','gold.patch','reference.patch'}];"
        f"paths={allowed};"
        "print(json.dumps({'blocked_paths':blocked,"
        "'missing_forbidden_roots':[p for p in ['/fixed','/source','/buggy','/protected'] if Path(p).exists()],"
        "'allowed_source_sha256':{p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in paths},"
        "'source_files':sum(p.is_file() for p in r.rglob('*'))}))"
    )
    result, _ = container(image, "python -c " + shlex.quote(code), output)
    if result["return_code"] != 0:
        raise RuntimeError("candidate audit process failed")
    audit = json.loads(result["stdout"])
    if audit["blocked_paths"] or audit["missing_forbidden_roots"]:
        raise ValueError("candidate contains forbidden artifacts")
    # Compare allowed source only to the BUGGY tree, never the fixed tree.
    original_code = (
        "import hashlib,json;from pathlib import Path;"
        f"r=Path('/buggy');paths={allowed};"
        "print(json.dumps({p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in paths}))"
    )
    original, _ = container(case["validator_source_image"], "python -c " + shlex.quote(original_code),
                            output.with_name("buggy_source_hashes.json"))
    if original["return_code"] != 0 or json.loads(original["stdout"]) != audit["allowed_source_sha256"]:
        raise ValueError("candidate source is not the declared buggy source")
    return audit


def build_case(case, frozen):
    case_id = case["case_id"]
    output = OUT / case_id
    if output.exists():
        if (output / "summary.json").exists():
            return json.loads((output / "summary.json").read_text(encoding="utf-8"))
        raise FileExistsError("incomplete prior candidate build; preserve and inspect before recovery")
    output.mkdir()
    package = {"pandas": "pandas", "matplotlib": "lib", "luigi": "luigi"}[case["project"]]
    # Stage 1 may read gold-containing validation images. Its layers are NOT
    # ancestors of either final image. Both finals start from the pinned base.
    prepare = (
        f"FROM {case['validator_source_image']} AS trusted\nUSER root\n"
        f"RUN mkdir /candidate /protected && cp -a /buggy/{package} /candidate/ && "
        "find /candidate -type d \\( -name tests -o -name test -o -name __pycache__ \\) -prune -exec rm -rf '{}' + && "
        "find /candidate -name .git -delete\n"
        "RUN cp -a /buggy/. /protected/ && rm -f /protected/.git && "
        "find /protected -type d -name __pycache__ -prune -exec rm -rf '{}' +\n"
        f"FROM {frozen['settings']['base_image']} AS candidate\n"
        "COPY --from=trusted /usr/local /usr/local\n"
        "COPY --from=trusted /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu\n"
        "COPY --from=trusted /candidate /candidate\n"
        "ENV PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg\n"
        "USER 65534:65534\nWORKDIR /tmp\n"
        "FROM candidate AS verifier\nUSER root\n"
        # /protected is the BUGGY tree with the public regression test file
        # used during preflight. It contains no fixed production source/history.
        "COPY --from=trusted /protected /protected\n"
        "USER 65534:65534\nWORKDIR /tmp\n"
    )
    dockerfile = output / "Dockerfile"
    dockerfile.write_text(prepare, encoding="utf-8")
    images = {}
    for target in ("candidate", "verifier"):
        tag = f"conveyorflow-bip-{case_id}-{target}:v2.3-v1"
        build = execute([executable(), "build", "--target", target, "-t", tag, str(output)],
                        timeout=frozen["settings"]["build_timeout_seconds"],
                        log=output / (target + "_build.json"))
        if build["return_code"] != 0:
            raise RuntimeError("candidate image build failed; retained build log")
        images[target] = inspect(tag)
    audit = image_audit(images["candidate"], case, output / "candidate_audit_execution.json")
    # The verifier's work tree is copied from read-only image data for each
    # invocation; no source repository or model credential is mounted.
    setup = "cp -a /protected /tmp/work && cd /tmp/work && "
    collect, _ = container(images["verifier"], setup +
        "PYTHONPATH=/tmp/work:/tmp/work/lib python -m pytest --collect-only -q " +
        shlex.quote(case["test_file"]), output / "regression_collection.json")
    if collect["return_code"] != 0:
        raise RuntimeError("regression collection failed")
    nodes = [line.strip() for line in collect["stdout"].splitlines()
             if line.startswith(case["test_file"] + "::") and
             not (line.strip() == case["visible_test"] or
                  line.strip().startswith(case["visible_test"] + "["))]
    seed = frozen["settings"]["regression_selection_seed"]
    nodes = sorted(set(nodes), key=lambda n: hashlib.sha256(f"{seed}|{case_id}|{n}".encode()).hexdigest())
    nodes = nodes[:frozen["settings"]["regression_items_per_case"]]
    if len(nodes) != frozen["settings"]["regression_items_per_case"]:
        raise ValueError("insufficient collected regression items; no replacements")
    write_new(output / "regression_selection.json", {"case_id": case_id, "nodeids": nodes,
               "rule": frozen["settings"]["regression_rule"], "frozen_before_test_outcomes": True})
    visible, visible_dir = container(images["verifier"], setup +
        "PYTHONPATH=/tmp/work:/tmp/work/lib python -m pytest -q " + shlex.quote(case["visible_test"]) +
        " --junitxml=/reports/tests.xml", output / "candidate_buggy_visible.json")
    regression, regression_dir = container(images["verifier"], setup +
        "PYTHONPATH=/tmp/work:/tmp/work/lib python -m pytest -q " + " ".join(shlex.quote(n) for n in nodes) +
        " --junitxml=/reports/tests.xml", output / "candidate_buggy_regression.json")
    fixed, fixed_dir = container(case["validator_source_image"],
        "cp -a /fixed /tmp/work && cd /tmp/work && PYTHONPATH=/tmp/work:/tmp/work/lib "
        "python -m pytest -q " + " ".join(shlex.quote(n) for n in nodes) +
        " --junitxml=/reports/tests.xml", output / "trusted_fixed_regression.json")
    vc, rc, fc = (test_counts(p / "tests.xml") for p in (visible_dir, regression_dir, fixed_dir))
    passed = (visible["return_code"] == 1 and vc["failures"] > 0 and vc["errors"] == 0
              and regression["return_code"] == fixed["return_code"] == 0
              and rc["tests"] == fc["tests"] == len(nodes) and rc["skipped"] == fc["skipped"] == 0)
    summary = {"case_id": case_id, "status": "candidate_preflight_passed" if passed else "candidate_preflight_failed",
               "no_llm_calls": True, "research_results": False, "images": images,
               "candidate_audit": audit, "visible_counts": vc, "regression_counts": rc,
               "fixed_regression_counts": fc, "regression_nodeids": nodes,
               "lock_sha256": sha(OUT / "lock.json"), "dockerfile_sha256": sha(dockerfile),
               "withheld_public_tests_not_novel_hidden_tests": True}
    write_new(output / "summary.json", summary)
    print(json.dumps({"case": case_id, "status": summary["status"], "no_llm_calls": True}), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-id")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    frozen = freeze()
    if args.all:
        for case in frozen["cases"]:
            result = build_case(case, frozen)
            if result["status"] != "candidate_preflight_passed":
                raise SystemExit("candidate regression preflight did not pass; no LLM call")
    elif args.case_id:
        case = next(c for c in frozen["cases"] if c["case_id"] == args.case_id)
        build_case(case, frozen)
    else:
        print(json.dumps({"status": frozen["status"], "cases": len(frozen["cases"]), "no_llm_calls": True}))


if __name__ == "__main__":
    main()
