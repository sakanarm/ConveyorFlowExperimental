"""Independent audit of the two adaptive FastAPI prompt follow-up attempts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE / "fastapi_llm_prompt_amendment_v1"
RAW = Path("D:/ConveyorFlowRuntime/v2_6/fastapi_llm_prompt_amendment_v1")
CAPSULE = ROOT / "audit_capsule_v1.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit():
    lock = read(ROOT / "lock.json")
    require(lock["status"] == "v2_6_fastapi_adaptive_prompt_amendment_frozen"
            and lock["exploratory_adaptive_follow_up"] is True and
            lock["not_pool_with_six_prior_attempts"] is True and
            lock["planned_provider_calls"] == 2,
            "Amendment scope drift")
    prior_lock = HERE / "fastapi_llm_feasibility_v1/lock.json"
    prior_audit = HERE / "fastapi_llm_feasibility_v1/audit_capsule_v1.json"
    require(lock["prior_lock_sha256"] == sha(prior_lock) and
            lock["prior_audit_sha256"] == sha(prior_audit),
            "Preceding diagnostic evidence drift")
    rows = [json.loads(line) for line in (ROOT / "ledger.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    require(len(rows) == len(lock["cases"]) == 2, "Incomplete amendment roster")
    audited = []
    ids = []
    for case, ledger in zip(lock["cases"], rows):
        case_id = case["case_id"]
        job = RAW / case_id / "agent_2"
        marker, summary = (read(job / name) for name in
                           ("request_started.json", "summary.json"))
        require(marker["case_id"] == summary["case_id"] == case_id and
                marker["slot"] == summary["slot"] == "agent_2" and
                marker["automatic_retry"] is False and
                marker["lock_sha256"] == sha(ROOT / "lock.json") and
                marker["prompt_sha256"] == case["prompt_sha256"] == sha(
                    RAW / case_id / "prompt.txt"),
                f"{case_id}: request marker drift")
        require(ledger == {"case_id": case_id, "slot": "agent_2",
                           "status": summary["status"],
                           "summary_sha256": sha(job / "summary.json")},
                f"{case_id}: ledger drift")
        if (job / "provider.json").exists():
            provider = read(job / "provider.json")
            require(sha(job / "response.txt") == summary["response_sha256"]
                    and provider["provider_request_id"] == summary[
                        "provider_request_id"]
                    and provider["exact_model_version"] == lock["model"][
                        "exact_version"],
                    f"{case_id}: provider evidence drift")
            ids.append(provider["provider_request_id"])
        else:
            require(summary["status"] == "PROVIDER_UNRESOLVED",
                    f"{case_id}: missing provider evidence")
        if (job / "patch.diff").exists():
            require(sha(job / "patch.diff") == summary["patch_sha256"],
                    f"{case_id}: patch hash drift")
            for check in summary.get("checks", []):
                folder = job / check["label"]
                execution = read(folder / "execution.json")
                xml = folder / "reports/tests.xml"
                cases = list(ET.fromstring(xml.read_bytes()).iter("testcase"))
                require(check["xml_sha256"] == sha(xml) and
                        check["return_code"] == execution["return_code"] and
                        len(cases) > 0,
                        f"{case_id}: raw verifier evidence drift")
                if check["okay"]:
                    require(check["return_code"] == 0 and not any(
                        child.tag in {"failure", "error"}
                        for item in cases for child in item),
                        f"{case_id}: false positive verifier pass")
        audited.append({"case_id": case_id, "status": summary["status"],
                        "summary_sha256": sha(job / "summary.json"),
                        "provider_request_id": summary.get("provider_request_id"),
                        "input_tokens": summary.get("input_tokens"),
                        "output_tokens": summary.get("output_tokens")})
    require(len(ids) == len(set(ids)), "Duplicate provider request identities")
    return {"status": "two_adaptive_attempts_audited_not_pooled",
            "adaptive_exploratory": True,
            "allocation_comparison": False,
            "attempts": audited,
            "verified_repairs": sum(row["status"] == "VERIFIED" for row in audited),
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
            require(read(CAPSULE) == result, "Existing capsule drift")
        else:
            with CAPSULE.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(result, stream, indent=2, sort_keys=True)
                stream.write("\n")
    print(json.dumps({key: value for key, value in result.items()
                      if key != "attempts"}, sort_keys=True))


if __name__ == "__main__":
    main()
