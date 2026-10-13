"""Create the executable MFEC config only from complete, allowlisted metadata evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
IMMUTABLE_VERSION_KEYS = ("deployment_id", "snapshot", "version")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def matching_records(probe: dict[str, Any], alias: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for endpoint in probe.get("probes", []):
        if endpoint.get("status") != "success":
            continue
        for record in endpoint.get("target_records", []):
            values = {str(value) for value in record.values() if value is not None}
            if alias in values:
                records.append(record)
    return records


def first_value(records: list[dict[str, Any]], keys: tuple[str, ...]) -> Any:
    for key in keys:
        for record in records:
            value = record.get(key)
            if value not in (None, ""):
                return value
    return None


def price_per_million(records: list[dict[str, Any]], direction: str) -> float | None:
    direct = first_value(records, (f"{direction}_cost_per_million_tokens",))
    if direct is not None:
        return float(direct)
    per_token = first_value(records, (f"{direction}_cost_per_token",))
    if per_token is not None:
        return float(per_token) * 1_000_000
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--candidate",
        type=Path,
        default=HERE / "config.mfec_final_team.json",
    )
    parser.add_argument(
        "--probe",
        type=Path,
        default=HERE / "mfec_metadata_probe.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE / "config.mfec_main_frozen.json",
    )
    parser.add_argument(
        "--calibration",
        type=Path,
        default=HERE / "mfec_calibration_probe.json",
    )
    args = parser.parse_args()

    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    probe = json.loads(args.probe.read_text(encoding="utf-8"))
    calibration = (
        json.loads(args.calibration.read_text(encoding="utf-8"))
        if args.calibration.is_file()
        else None
    )
    frozen = deepcopy(candidate)
    unresolved: list[dict[str, Any]] = []
    resolved_versions: set[str] = set()

    for model in frozen.get("models", []):
        alias = str(model["model_id"])
        records = matching_records(probe, alias)
        version = first_value(records, IMMUTABLE_VERSION_KEYS)
        input_price = price_per_million(records, "input")
        output_price = price_per_million(records, "output")
        calibrated = None
        if calibration:
            calibrated = next(
                (item for item in calibration.get("models", []) if item.get("model_id") == alias),
                None,
            )
            if version is None and calibrated:
                version = calibrated.get("deployment_id")
        missing = []
        if version is None:
            missing.append("immutable_version_or_deployment_id")
        provider_cost_ready = bool(
            calibrated
            and calibrated.get("response_cost_header_present") is True
            and calibrated.get("session_id")
        )
        if input_price is None and not provider_cost_ready:
            missing.append("input_price_or_provider_response_cost")
        if output_price is None and not provider_cost_ready:
            missing.append("output_price_or_provider_response_cost")
        if missing:
            unresolved.append({"model_id": alias, "missing": missing})
            continue
        version_text = str(version)
        if version_text in resolved_versions:
            unresolved.append(
                {"model_id": alias, "missing": ["distinct_immutable_version_identity"]}
            )
            continue
        resolved_versions.add(version_text)
        model["exact_version"] = version_text
        if provider_cost_ready:
            model["cost_accounting_mode"] = "provider_response_header"
            model["session_id"] = str(calibrated["session_id"])
        else:
            model["input_price_per_million_tokens"] = float(input_price)
            model["output_price_per_million_tokens"] = float(output_price)
            model["cost_accounting_mode"] = "frozen_token_prices"

    if unresolved:
        print(json.dumps({"status": "blocked", "unresolved": unresolved}, indent=2))
        return 2

    frozen["study_status"] = "FROZEN_FOR_EXECUTION"
    frozen["blocking_fields"] = []
    frozen["metadata_evidence"] = {
        "path": args.probe.name,
        "sha256": sha256(args.probe),
        "retrieved_at_utc": probe.get("retrieved_at_utc"),
        "contains_credentials": False,
    }
    frozen["runner_evidence"] = {
        "path": "run_pilot.py",
        "sha256": sha256(HERE / "run_pilot.py"),
    }
    if calibration:
        frozen["calibration_evidence"] = {
            "path": args.calibration.name,
            "sha256": sha256(args.calibration),
            "retrieved_at_utc": calibration.get("retrieved_at_utc"),
            "contains_credentials": False,
        }
    args.output.write_text(json.dumps(frozen, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "frozen",
                "output": str(args.output),
                "sha256": sha256(args.output),
                "models": len(frozen.get("models", [])),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
