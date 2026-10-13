"""Securely probe MFEC LiteLLM metadata endpoints for version and price fields.

The API key is read with getpass and is never written. Only allowlisted,
non-secret metadata fields for the three selected aliases are persisted.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
TARGETS = {"tencent-hy3", "gpt-5-mini", "glm-5.3-flash"}
SAFE_KEYS = {
    "id",
    "model_name",
    "model",
    "model_id",
    "litellm_model_name",
    "provider",
    "mode",
    "version",
    "snapshot",
    "deployment_id",
    "input_cost_per_token",
    "output_cost_per_token",
    "input_cost_per_million_tokens",
    "output_cost_per_million_tokens",
    "effective_from",
    "effective_to",
    "updated_at",
}
ENDPOINTS = (
    "/model/info",
    "/v1/model/info",
    "/model_group/info",
    "/v1/models",
)


def request_json(url: str, key: str, timeout: int) -> Any:
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def safe_target_records(payload: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in walk(payload):
        text_values = {str(value) for value in item.values() if isinstance(value, (str, int, float))}
        if not any(target in text_values for target in TARGETS):
            continue
        safe = {key: item[key] for key in SAFE_KEYS if key in item}
        fingerprint = json.dumps(safe, sort_keys=True, default=str)
        if safe and fingerprint not in seen:
            records.append(safe)
            seen.add(fingerprint)
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://gpt.mfec.co.th/litellm")
    parser.add_argument("--output", type=Path, default=HERE / "mfec_metadata_probe.json")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    api_key = os.environ.get("MFEC_LITELLM_API_KEY") or getpass.getpass(
        "MFEC LiteLLM API key (hidden): "
    )
    if not api_key.strip():
        raise SystemExit("empty API key")
    probes: list[dict[str, Any]] = []
    try:
        for endpoint in ENDPOINTS:
            url = f"{args.base_url.rstrip('/')}{endpoint}"
            try:
                payload = request_json(url, api_key, args.timeout)
                records = safe_target_records(payload)
                probes.append(
                    {
                        "endpoint": endpoint,
                        "status": "success",
                        "target_records": records,
                        "target_record_count": len(records),
                    }
                )
            except urllib.error.HTTPError as exc:
                probes.append({"endpoint": endpoint, "status": f"http_{exc.code}"})
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                probes.append({"endpoint": endpoint, "status": type(exc).__name__})
    finally:
        api_key = ""  # best-effort removal from the live Python reference
    result = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "targets": sorted(TARGETS),
        "contains_credentials": False,
        "probes": probes,
        "mapping_complete": all(
            any(
                target in {str(value) for value in record.values()}
                and any(key in record for key in ("version", "snapshot", "deployment_id", "litellm_model_name"))
                for probe in probes
                for record in probe.get("target_records", [])
            )
            for target in TARGETS
        ),
        "pricing_complete": all(
            any(
                target in {str(value) for value in record.values()}
                and any("input_cost" in key for key in record)
                and any("output_cost" in key for key in record)
                for probe in probes
                for record in probe.get("target_records", [])
            )
            for target in TARGETS
        ),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
