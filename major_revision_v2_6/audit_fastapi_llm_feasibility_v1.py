"""Read-only audit of the six frozen FastAPI Real-LLM diagnostic attempts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE / "fastapi_llm_feasibility_v1"
RAW = Path("D:/ConveyorFlowRuntime/v2_6/fastapi_llm_feasibility_v1")
CAPSULE = ROOT / "audit_capsule_v1.json"


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def junit(path: Path):
    root = ET.fromstring(path.read_bytes())
    cases = list(root.iter("testcase"))
    return {"tests": len(cases),
            "failures": sum(any(c.tag == "failure" for c in case)
                            for case in cases),
            "errors": sum(any(c.tag == "error" for c in case)
                          for case in cases)}


def audit():
    lock = read(ROOT / "lock.json")
    require(lock["status"] == "v2_6_fastapi_bounded_repair_diagnostic_frozen"
            and lock["planned_provider_calls"] == 6 and
            lock["independent_repository_projects"] == 1 and
            lock["allocation_comparison"] is False,
            "Design scope changed")
    rows = [json.loads(line) for line in (ROOT / "ledger.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    pairs = [(case, model) for case in lock["cases"] for model in lock["models"]]
    require(len(rows) == len(pairs) == 6, "Incomplete frozen attempt roster")
    ids = []
    audited = []
    for (case, model), ledger in zip(pairs, rows):
        case_id, slot = case["case_id"], model["slot"]
        job = RAW / case_id / slot
        started_path, summary_path = (job / name for name in
                                      ("request_started.json", "summary.json"))
        started, summary = read(started_path), read(summary_path)
        require(started["case_id"] == summary["case_id"] == case_id and
                started["model_slot"] == summary["slot"] == slot and
                started["lock_sha256"] == sha(ROOT / "lock.json") and
                started["prompt_sha256"] == case["prompt_sha256"] == sha(
                    RAW / case_id / "prompt.txt") and
                started["automatic_retry"] is False,
                f"{case_id}/{slot}: request marker drift")
        require(ledger == {"case_id": case_id, "slot": slot,
                           "status": summary["status"],
                           "summary_sha256": sha(summary_path)},
                f"{case_id}/{slot}: ledger drift")
        provider_path = job / "provider.json"
        if provider_path.exists():
            provider = read(provider_path)
            response = job / "response.txt"
            require(sha(response) == summary["response_sha256"] and
                    provider["provider_request_id"] == summary["provider_request_id"]
                    and provider["exact_model_version"] == model["exact_version"]
                    and provider["input_tokens"] == summary["input_tokens"]
                    and provider["output_tokens"] == summary["output_tokens"],
                    f"{case_id}/{slot}: provider evidence drift")
            ids.append(provider["provider_request_id"])
        elif summary["status"] != "PROVIDER_UNRESOLVED":
            raise ValueError(f"{case_id}/{slot}: missing provider evidence")
        patch = job / "patch.diff"
        if patch.exists():
            require(sha(patch) == summary["patch_sha256"],
                    f"{case_id}/{slot}: patch hash drift")
            for check in summary.get("checks", []):
                label = check["label"]
                execution = read(job / label / "execution.json")
                xml = job / label / "reports/tests.xml"
                counts = junit(xml)
                require(sha(xml) == check["xml_sha256"] and
                        execution["return_code"] == check["return_code"] and
                        counts["tests"] > 0,
                        f"{case_id}/{slot}/{label}: raw test evidence drift")
                if check["okay"]:
                    require(counts["failures"] == counts["errors"] == 0 and
                            check["return_code"] == 0,
                            f"{case_id}/{slot}/{label}: false pass")
        audited.append({"case_id": case_id, "slot": slot,
                        "status": summary["status"],
                        "request_marker_sha256": sha(started_path),
                        "summary_sha256": sha(summary_path),
                        "provider_request_id": summary.get("provider_request_id"),
                        "input_tokens": summary.get("input_tokens"),
                        "output_tokens": summary.get("output_tokens"),
                        "reported_cost_units": summary.get("response_cost")})
    require(len(ids) == len(set(ids)), "Duplicate provider request IDs")
    statuses = {status: sum(row["status"] == status for row in audited)
                for status in sorted({row["status"] for row in audited})}
    return {"status": "six_diagnostic_attempts_independently_audited",
            "allocation_comparison": False, "repository_projects": 1,
            "cases": 2, "provider_attempts": 6,
            "verified_repairs": statuses.get("VERIFIED", 0),
            "status_counts": statuses, "attempts": audited,
            "currency_known": False, "monetary_cost_claim_allowed": False,
            "lock_sha256": sha(ROOT / "lock.json"),
            "ledger_sha256": sha(ROOT / "ledger.jsonl"),
            "raw_root": str(RAW)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.write:
        if CAPSULE.exists():
            require(read(CAPSULE) == result, "Existing audit capsule drift")
        else:
            with CAPSULE.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(result, stream, indent=2, sort_keys=True)
                stream.write("\n")
    print(json.dumps({key: value for key, value in result.items()
                      if key != "attempts"}, sort_keys=True))


if __name__ == "__main__":
    main()
