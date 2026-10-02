"""Deterministic validator copied into every frozen Real-LLM case bundle."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def extract_json(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("no JSON object found")


def compare(expected: Any, actual: Any, tolerance: float, path: str = "answer") -> list[str]:
    errors: list[str] = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected object"]
        for key, value in expected.items():
            if key not in actual:
                errors.append(f"{path}.{key}: missing")
            else:
                errors.extend(compare(value, actual[key], tolerance, f"{path}.{key}"))
        return errors
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return [f"{path}: list length/type mismatch"]
        for index, (left, right) in enumerate(zip(expected, actual)):
            errors.extend(compare(left, right, tolerance, f"{path}[{index}]"))
        return errors
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            return [f"{path}: expected numeric"]
        if not math.isfinite(float(actual)) or abs(float(expected) - float(actual)) > tolerance:
            return [f"{path}: numeric mismatch"]
        return []
    if expected != actual:
        errors.append(f"{path}: value mismatch")
    return errors


def apply_integer_action(action: str, x: int, y: int) -> int:
    actions = {
        "add": lambda: x + y,
        "subtract": lambda: x - y,
        "multiply": lambda: x * y,
        "floor_divide_safe": lambda: x // y if y else 0,
        "maximum": lambda: max(x, y),
        "minimum": lambda: min(x, y),
        "absolute_difference": lambda: abs(x - y),
        "increment_by_one": lambda: x + 1,
        "decrement_by_one": lambda: x - 1,
        "clamp_nonnegative": lambda: max(0, x),
        "clamp_upper": lambda: min(x, y),
        "clamp_lower": lambda: max(x, y),
        "modulo_safe": lambda: x % y if y else 0,
        "square_plus": lambda: x * x + y,
        "choose_x_if_nonzero_else_y": lambda: x if x != 0 else y,
        "distance_plus_one": lambda: abs(x - y) + 1,
    }
    if action not in actions:
        raise ValueError("unknown repair_action")
    return int(actions[action]())


def validate(candidate: dict[str, Any], specification: dict[str, Any]) -> tuple[bool, list[str]]:
    answer = candidate.get("answer")
    if not isinstance(answer, dict):
        return False, ["answer: missing object"]
    validator_type = specification["validator_type"]
    if validator_type == "numeric_json":
        errors = compare(
            specification["answer"], answer, float(specification.get("tolerance", 0.01))
        )
        return not errors, errors
    if validator_type == "behavioral_integer_repair":
        action = answer.get("repair_action")
        errors: list[str] = []
        for index, test in enumerate(specification["hidden_tests"]):
            try:
                observed = apply_integer_action(str(action), int(test["x"]), int(test["y"]))
            except (TypeError, ValueError) as exc:
                return False, [f"repair_action: {exc}"]
            if observed != int(test["expected"]):
                errors.append(f"hidden_test_{index}: behavior mismatch")
        return not errors, errors
    return False, ["unsupported validator_type"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    args = parser.parse_args()
    try:
        candidate = extract_json(Path(args.candidate).read_text(encoding="utf-8"))
        specification = json.loads(
            (Path(__file__).resolve().parent / "expected.json").read_text(encoding="utf-8")
        )
        passed, errors = validate(candidate, specification)
        result = {
            "passed": passed,
            "validator_type": specification["validator_type"],
            "checks": len(specification.get("hidden_tests", specification.get("answer", {}))),
            "errors": errors[:10],
        }
    except Exception as exc:
        result = {"passed": False, "validator_type": "unknown", "checks": 0, "errors": [str(exc)]}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
