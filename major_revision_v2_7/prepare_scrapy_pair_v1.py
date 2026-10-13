"""Gold-free, pre-provider Scrapy candidate gate for a bounded v2.7 pair.

This is a repository-only feasibility extension, not the mixed-source main
cohort. Test identities and exclusions are selected before any Scrapy LLM call.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
V2 = HERE.parent
ROOT = HERE / "scrapy_pair_v1b"
LOCK = ROOT / "candidate_lock.json"
RAW = Path("/mnt/d/ConveyorFlowRuntime/v2_7/scrapy_pair_v1b")
SOURCE = V2 / "major_revision_v2_6"
PREFLIGHT = Path("/mnt/d/ConveyorFlowRuntime/v2_6/scrapy_public_preflight_v1b")
QUEUE = SOURCE / "scrapy_source_queue_v1/queue.json"
AUDIT_LOCK = SOURCE / "scrapy_public_preflight_v1b/lock.json"
ALLOWED = {
    "scrapy_39": ["scrapy/spiders/__init__.py"],
    "scrapy_34": ["scrapy/item.py"],
}
CASE_DIRS = {"scrapy_39": "00_scrapy_39", "scrapy_34": "01_scrapy_34"}
REGRESSION_COUNT = 5
MAX_REGRESSION_SCAN = 30


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def run_container(image, variant, command, timeout=180):
    if variant not in {"buggy", "fixed"}:
        raise ValueError("Invalid validator variant")
    script = (f"cp -a /{variant} /tmp/work && cd /tmp/work && "
              "PYTHONPATH=/tmp/work " + command)
    return subprocess.run(
        ["podman", "run", "--rm", "--network", "none", "--read-only",
         "--cpus", "2", "--memory", "4g", "--pids-limit", "256",
         "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
         "--user", "65534:65534", "--tmpfs", "/tmp:rw,nosuid,size=2147483648",
         image, "sh", "-c", script], capture_output=True, text=True,
        errors="replace", timeout=timeout,
        env={k: v for k, v in os.environ.items() if k != "MFEC_LITELLM_API_KEY"})


def extract(image, paths):
    code = ("import json;from pathlib import Path;"
            f"names={paths!r};"
            "print(json.dumps({n:(Path('/buggy')/n).read_text(encoding='utf-8') "
            "for n in names},sort_keys=True))")
    result = subprocess.run(
        ["podman", "run", "--rm", "--network", "none", "--read-only",
         "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
         image, "python", "-c", code], capture_output=True, text=True,
        errors="replace", timeout=180,
        env={k: v for k, v in os.environ.items() if k != "MFEC_LITELLM_API_KEY"})
    if result.returncode:
        raise RuntimeError("Buggy source extraction failed: " + result.stderr[-500:])
    return json.loads(result.stdout)


def all_nodes(image, module):
    code = (
        "import unittest,json;"
        "s=unittest.defaultTestLoader.loadTestsFromName('" + module + "')\n"
        "def walk(x):\n"
        " if isinstance(x,unittest.TestSuite):\n"
        "  for y in x: yield from walk(y)\n"
        " else: yield x.id()\n"
        "print(json.dumps(sorted(walk(s))))")
    result = run_container(image, "buggy", "python -c " + "'" + code.replace("'", "'\\''") + "'")
    if result.returncode:
        raise RuntimeError("Could not enumerate public unittest IDs: " + result.stderr[-500:])
    ids = json.loads(result.stdout.strip().splitlines()[-1])
    if not ids or not all(node.startswith(module + ".") for node in ids):
        raise ValueError("Public test inventory mismatch")
    return ids


def test_node(image, variant, node):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]+", node):
        raise ValueError("Invalid public test ID")
    result = run_container(image, variant, "python -m unittest -q " + node)
    output = result.stdout + "\n" + result.stderr
    okay = (result.returncode == 0 and
            bool(re.search(r"Ran [1-9][0-9]* tests? in", output)) and
            bool(re.search(r"(?:^|\n)OK(?:\n|$)", output)))
    return {"node": node, "variant": variant, "return_code": result.returncode,
            "okay": okay, "stdout_tail": result.stdout[-1500:],
            "stderr_tail": result.stderr[-1500:]}


def prepare():
    if sys.platform != "linux" or os.geteuid() != 0 or os.environ.get(
            "CONVEYORFLOW_CONTAINER_COMMAND") != "podman":
        raise ValueError("Rootful Linux/Podman required")
    if ROOT.exists() or RAW.exists():
        raise FileExistsError("Existing candidate gate: audit, do not overwrite")
    preflight = read(AUDIT_LOCK)
    if preflight["provider_calls"] != 0:
        raise ValueError("Source preflight was not pre-provider")
    source_queue = read(QUEUE)
    if [row["case_id"] for row in source_queue[:2]] != list(ALLOWED):
        raise ValueError("Frozen source queue order drift")
    ROOT.mkdir()
    RAW.mkdir(parents=True)
    result = {
        "status": "v2_7_scrapy_gold_free_candidate_gate",
        "claim_scope": "Two bugs in one Scrapy repository; not mixed main or an independent-project estimate",
        "provider_calls": 0,
        "preflight_lock_sha256": sha(AUDIT_LOCK),
        "queue_sha256": sha(QUEUE),
        "runner_sha256": sha(__file__),
        "regression_selection_rule": (
            "Within each same public test module, hash-sort IDs by sha256(case_id + ':' + ID); "
            "exclude visible nodes; scan at most 30, retain first 5 that pass on both buggy and fixed"),
        "case_order": list(ALLOWED),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "cases": [],
    }
    for case_id, allowed in ALLOWED.items():
        source_dir = PREFLIGHT / CASE_DIRS[case_id]
        record_path = source_dir / "preflight_record.json"
        record = read(record_path)
        if record["status"] != "reproducible" or record["provider_calls"] != 0:
            raise ValueError("Unqualified source " + case_id)
        image = record["container_image_id"]
        inspected = subprocess.run(
            ["podman", "image", "inspect", image, "--format", "{{.Id}}"],
            capture_output=True, text=True, timeout=60)
        if inspected.returncode or inspected.stdout.strip().removeprefix("sha256:") != image.removeprefix("sha256:"):
            raise ValueError("Pinned validator image absent")
        source = extract(image, allowed)
        public_commands = record["public_commands"]
        visible = [row[-1] for row in public_commands]
        module = ".".join(visible[0].split(".")[:2])
        if not all(node.startswith(module + ".") for node in visible):
            raise ValueError("Visible test module mismatch")
        nodes = all_nodes(image, module)
        candidates = sorted((node for node in nodes if node not in visible),
                            key=lambda node: digest((case_id + ":" + node).encode()))
        checks = []
        selected = []
        for node in candidates[:MAX_REGRESSION_SCAN]:
            pair = [test_node(image, variant, node) for variant in ("buggy", "fixed")]
            checks.append({"node": node, "pair": pair})
            if all(row["okay"] for row in pair):
                selected.append(node)
            if len(selected) == REGRESSION_COUNT:
                break
        case_out = RAW / case_id
        case_out.mkdir()
        save_new(case_out / "regression_checks.json", checks)
        if len(selected) != REGRESSION_COUNT:
            raise ValueError("Insufficient pass-pass public regression nodes for " + case_id)
        failure_paths = sorted((source_dir / "buggy").glob("command_*/execution.json"))
        failure = []
        for path in failure_paths:
            execution = read(path)
            failure.append((execution.get("stdout", "") + "\n" +
                            execution.get("stderr", ""))[-3000:])
        instruction = (
            'Repair the supplied buggy Python source. Emit JSON only: '
            '{"edits":[{"path":"allowed/path.py","before":"exact unique substring copied from buggy source",'
            '"after":"replacement substring"}]}. Use one to eight nonoverlapping edits; '
            'before must match exactly once in the original full file. Modify only allowed production '
            'files. Do not alter tests. Python 3.8.20. Return only JSON, no reasoning or markdown.\n')
        context = {"case_id": case_id, "allowed_source_files": source,
                   "public_visible_nodes": visible,
                   "public_failure_tails": failure,
                   "repair_scope": "Only listed buggy production files; fixed source not provided."}
        prompt = instruction + json.dumps(context, ensure_ascii=False)
        (case_out / "prompt.txt").write_text(prompt, encoding="utf-8")
        result["cases"].append({
            "case_id": case_id, "preflight_record_sha256": sha(record_path),
            "validator_image": image, "allowed_files": allowed,
            "source_sha256": {p: digest(s.encode("utf-8")) for p, s in source.items()},
            "visible_nodes": visible, "regression_nodes": selected,
            "regression_checks_sha256": sha(case_out / "regression_checks.json"),
            "prompt_sha256": sha(case_out / "prompt.txt"),
            "public_failure_execution_sha256": [sha(p) for p in failure_paths],
        })
    save_new(LOCK, result)
    return {"status": "candidate_gate_ready_before_provider", "cases": len(result["cases"]),
            "lock_sha256": sha(LOCK), "provider_calls": 0}


def audit():
    lock = read(LOCK)
    if lock["runner_sha256"] != sha(__file__) or lock["preflight_lock_sha256"] != sha(AUDIT_LOCK):
        raise ValueError("Candidate gate dependency drift")
    for case in lock["cases"]:
        case_id = case["case_id"]
        source_dir = PREFLIGHT / CASE_DIRS[case_id]
        prompt = RAW / case_id / "prompt.txt"
        checks_path = RAW / case_id / "regression_checks.json"
        if (sha(prompt) != case["prompt_sha256"] or
                sha(checks_path) != case["regression_checks_sha256"] or
                sha(source_dir / "preflight_record.json") != case["preflight_record_sha256"]):
            raise ValueError("Candidate evidence drift")
        checks = read(checks_path)
        selected = [row["node"] for row in checks if all(p["okay"] for p in row["pair"])]
        if selected != case["regression_nodes"] or len(selected) != REGRESSION_COUNT:
            raise ValueError("Regression gate drift")
        if not all(node not in case["visible_nodes"] for node in selected):
            raise ValueError("Visible/regression overlap")
        source = extract(case["validator_image"], case["allowed_files"])
        if {p: digest(s.encode("utf-8")) for p, s in source.items()} != case["source_sha256"]:
            raise ValueError("Buggy source drift")
        if "/fixed/" in prompt.read_text(encoding="utf-8"):
            raise ValueError("Fixed source path leaked to prompt")
    return {"status": "candidate_gate_audited", "cases": len(lock["cases"]),
            "lock_sha256": sha(LOCK), "provider_calls": 0}


def smoke():
    if sys.platform != "linux" or os.geteuid() != 0:
        raise ValueError("Linux root required")
    rows = []
    for case_id in ALLOWED:
        record = read(PREFLIGHT / CASE_DIRS[case_id] / "preflight_record.json")
        module = ".".join(record["public_commands"][0][-1].split(".")[:2])
        rows.append({"case_id": case_id,
                     "source_files": list(extract(record["container_image_id"], ALLOWED[case_id])),
                     "public_module_test_count": len(all_nodes(record["container_image_id"], module))})
    return {"status": "read_only_smoke", "rows": rows, "provider_calls": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--audit", action="store_true")
    group.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    print(json.dumps(prepare() if args.prepare else audit() if args.audit else smoke(),
                     sort_keys=True), flush=True)
