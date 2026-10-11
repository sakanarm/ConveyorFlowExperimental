"""One paid MFEC gateway probe. Operational check, not a research outcome.

Creates an immutable receipt without persisting credentials or model text.
The probe is deliberately excluded from paired blocks and sample counts.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
V2 = HERE.parent
sys.path.insert(0, str(V2 / "real_llm_pilot"))
from mfec_adapter import invoke  # noqa: E402


def main() -> None:
    receipt = HERE / "results" / "mfec_gateway_probe_v1.json"
    if receipt.exists():
        raise FileExistsError("Probe already recorded; do not repeat this attempt")
    config = json.loads((V2 / "real_llm_pilot" / "config.mfec_main_frozen.json").read_text(encoding="utf-8"))
    model = config["models"][1]
    response = invoke(
        model={**model, "base_url": config["base_url"]},
        case={"prompt": 'Operational probe only. Return exactly {"probe":"ok"}.'},
        generation={"temperature": 0, "max_output_tokens": 64, "timeout_seconds": 120},
    )
    row = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "gateway_probe_passed" if '"probe":"ok"' in response["content"].replace(" ", "") else "gateway_response_unexpected",
        "research_results": False,
        "paired_block": False,
        "model_id": model["model_id"],
        "provider_request_id": response["provider_request_id"],
        "returned_model_version": response["exact_model_version"],
        "input_tokens": response["input_tokens"],
        "output_tokens": response["output_tokens"],
        "latency_seconds": response["latency_seconds"],
        "finish_reason": response["finish_reason"],
        "response_content_sha256": hashlib.sha256(response["content"].encode("utf-8")).hexdigest(),
        "reported_response_cost": response.get("response_cost"),
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with receipt.open("x", encoding="utf-8") as handle:
        json.dump(row, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"status": row["status"], "request_recorded": True, "research_results": False}))


if __name__ == "__main__":
    main()
