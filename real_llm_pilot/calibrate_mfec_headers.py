"""Make one minimal call per MFEC alias and persist only safe routing/cost evidence."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent


def call(base_url: str, key: str, model: dict[str, Any], timeout: int) -> dict[str, Any]:
    alias = str(model["model_id"])
    slot = str(model["slot"])
    session_id = f"conveyorflow-v2-main-{slot}"
    body = json.dumps(
        {
            "model": alias,
            "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
            "temperature": 0,
            "max_tokens": 8,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-litellm-session-id": session_id,
        },
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
        headers = {name.lower(): value for name, value in response.headers.items()}
    usage = payload.get("usage") or {}
    deployment_id = headers.get("x-litellm-model-id")
    response_cost = headers.get("x-litellm-response-cost")
    return {
        "slot": slot,
        "model_id": alias,
        "session_id": session_id,
        "deployment_id": deployment_id,
        "payload_model": payload.get("model"),
        "proxy_version": headers.get("x-litellm-version"),
        "response_cost_header_present": response_cost not in (None, ""),
        "calibration_response_cost": float(response_cost) if response_cost not in (None, "") else None,
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
        "provider_request_id": payload.get("id") or headers.get("x-request-id"),
        "latency_seconds": time.perf_counter() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=HERE / "config.mfec_final_team.json")
    parser.add_argument("--output", type=Path, default=HERE / "mfec_calibration_probe.json")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    key = os.environ.get("MFEC_LITELLM_API_KEY") or getpass.getpass(
        "MFEC LiteLLM API key (hidden): "
    )
    if not key.strip():
        raise SystemExit("empty API key")
    try:
        models = [call(config["base_url"], key, model, args.timeout) for model in config["models"]]
    finally:
        key = ""
    deployment_ids = [item.get("deployment_id") for item in models]
    ready = (
        all(deployment_ids)
        and len(set(deployment_ids)) == len(deployment_ids)
        and all(item["response_cost_header_present"] for item in models)
    )
    result = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": config["base_url"],
        "contains_credentials": False,
        "billable_calibration_calls": len(models),
        "ready_for_freeze": ready,
        "models": models,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
