"""OpenAI-compatible MFEC LiteLLM adapter for the frozen study runner."""

from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any


def invoke(*, model: dict[str, Any], case: dict[str, Any], generation: dict[str, Any]) -> dict[str, Any]:
    key_name = str(model.get("api_key_env", "MFEC_LITELLM_API_KEY"))
    api_key = os.environ.get(key_name)
    if not api_key:
        raise ValueError(f"required API-key environment variable is not set: {key_name}")
    prompt = case.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("runner must supply the frozen case prompt")
    base_url = str(model.get("base_url") or case.get("base_url") or "https://gpt.mfec.co.th/litellm")
    endpoint = f"{base_url.rstrip('/')}/v1/chat/completions"
    body = json.dumps(
        {
            "model": model["model_id"],
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Solve the supplied research microtask. Follow its JSON schema exactly. "
                        "Return no prose or markdown outside the JSON object."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": generation.get("temperature", 0),
            "max_tokens": int(generation.get("max_output_tokens", 4096)),
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            **(
                {"x-litellm-session-id": str(model["session_id"])}
                if model.get("session_id")
                else {}
            ),
        },
    )
    started = time.perf_counter()
    with urllib.request.urlopen(
        request, timeout=int(generation.get("timeout_seconds", 180))
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
        headers = {key.lower(): value for key, value in response.headers.items()}
    latency = time.perf_counter() - started
    choice = payload["choices"][0]
    usage = payload.get("usage") or {}
    input_tokens = usage.get("prompt_tokens")
    output_tokens = usage.get("completion_tokens")
    if input_tokens is None or output_tokens is None:
        raise ValueError("MFEC response omitted prompt/completion token counts")
    returned_version = (
        headers.get("x-litellm-model-id")
        or headers.get("x-litellm-model-version")
        or payload.get("model")
    )
    if not returned_version:
        raise ValueError("MFEC response omitted model/version identity")
    request_id = payload.get("id") or headers.get("x-request-id")
    if not request_id:
        raise ValueError("MFEC response omitted provider request ID")
    result = {
        "content": choice.get("message", {}).get("content", ""),
        "provider_request_id": str(request_id),
        "exact_model_version": str(returned_version),
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "latency_seconds": float(latency),
        "finish_reason": str(choice.get("finish_reason") or "unknown"),
    }
    response_cost = headers.get("x-litellm-response-cost")
    if response_cost not in (None, ""):
        result["response_cost"] = float(response_cost)
    return result
