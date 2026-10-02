from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "real_llm_pilot" / "mfec_adapter.py"
SPEC = importlib.util.spec_from_file_location("mfec_adapter_test", PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakeResponse:
    def __init__(self, payload: dict, headers: dict[str, str] | None = None) -> None:
        self.payload = payload
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_adapter_returns_auditable_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_MFEC_KEY", "secret-not-written")
    payload = {
        "id": "req-1",
        "model": "alias-only",
        "choices": [{"message": {"content": '{"answer": {}}'}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 4},
    }
    monkeypatch.setattr(
        MODULE.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(
            payload, {"x-litellm-model-version": "provider/model@immutable"}
        ),
    )

    result = MODULE.invoke(
        model={
            "model_id": "alias",
            "api_key_env": "TEST_MFEC_KEY",
            "base_url": "https://example.invalid",
        },
        case={"prompt": "Return JSON."},
        generation={"temperature": 0, "max_output_tokens": 20, "timeout_seconds": 5},
    )

    assert result["provider_request_id"] == "req-1"
    assert result["exact_model_version"] == "provider/model@immutable"
    assert result["input_tokens"] == 12
    assert result["output_tokens"] == 4
    assert "secret-not-written" not in json.dumps(result)


def test_adapter_requires_hidden_environment_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISSING_KEY", raising=False)
    with pytest.raises(ValueError, match="not set"):
        MODULE.invoke(
            model={"model_id": "m", "api_key_env": "MISSING_KEY"},
            case={"prompt": "Return JSON."},
            generation={},
        )
