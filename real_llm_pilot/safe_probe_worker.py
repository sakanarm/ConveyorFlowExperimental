from __future__ import annotations

import json
import math
import sys
from typing import Any


SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
    "ValueError": ValueError,
    "TypeError": TypeError,
}


def equivalent(actual: Any, expected: Any, tolerance: float = 1e-8) -> bool:
    if isinstance(expected, bool) or expected is None or isinstance(expected, str):
        return actual == expected
    if isinstance(expected, (int, float)):
        try:
            return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=tolerance)
        except (TypeError, ValueError):
            return False
    if isinstance(expected, list):
        return isinstance(actual, (list, tuple)) and len(actual) == len(expected) and all(
            equivalent(a, e, tolerance) for a, e in zip(actual, expected)
        )
    if isinstance(expected, dict):
        return isinstance(actual, dict) and set(actual) == set(expected) and all(
            equivalent(actual[key], value, tolerance) for key, value in expected.items()
        )
    return actual == expected


def main() -> int:
    payload = json.load(sys.stdin)
    namespace: dict[str, Any] = {"__builtins__": SAFE_BUILTINS}
    try:
        exec(compile(payload["code"], "<candidate>", "exec"), namespace, namespace)
        function = namespace[payload["function_name"]]
    except Exception as exc:  # noqa: BLE001 - isolated worker returns a category only
        print(json.dumps({"passed": False, "reason": f"load_error:{type(exc).__name__}"}))
        return 0

    results = []
    for index, test in enumerate(payload["tests"], start=1):
        try:
            actual = function(*test.get("args", []), **test.get("kwargs", {}))
            passed = equivalent(actual, test["expected"], float(test.get("tolerance", 1e-8)))
            results.append({"test": index, "passed": passed})
        except Exception as exc:  # noqa: BLE001 - isolated worker returns a category only
            results.append({"test": index, "passed": False, "error": type(exc).__name__})
    passed = bool(results) and all(row["passed"] for row in results)
    print(json.dumps({"passed": passed, "reason": "pass" if passed else "unit_test_failure", "tests": results}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
