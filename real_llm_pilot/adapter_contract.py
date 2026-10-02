from __future__ import annotations

from typing import Any, Protocol, TypedDict


class AdapterResponse(TypedDict):
    content: str
    provider_request_id: str
    exact_model_version: str
    input_tokens: int
    output_tokens: int
    latency_seconds: float
    finish_reason: str
    response_cost: float


class ProviderAdapter(Protocol):
    def invoke(self, *, model: dict[str, Any], case: dict[str, Any], generation: dict[str, Any]) -> AdapterResponse:
        """Call one pinned model version and return complete auditable usage metadata."""


REQUIRED_RESPONSE_FIELDS = {
    "content",
    "provider_request_id",
    "exact_model_version",
    "input_tokens",
    "output_tokens",
    "latency_seconds",
    "finish_reason",
}


def validate_response(response: dict[str, Any]) -> None:
    missing = REQUIRED_RESPONSE_FIELDS - set(response)
    if missing:
        raise ValueError(f"adapter response missing fields: {sorted(missing)}")
    if response["input_tokens"] < 0 or response["output_tokens"] < 0:
        raise ValueError("token counts must be non-negative")
    if response["latency_seconds"] < 0:
        raise ValueError("latency_seconds must be non-negative")
    if "response_cost" in response and response["response_cost"] < 0:
        raise ValueError("response_cost must be non-negative")
