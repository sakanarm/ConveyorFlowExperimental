from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
WORKER = HERE / "safe_probe_worker.py"
OUTPUT = HERE / "calibration_fixbug_v2.jsonl"


def probe(
    probe_id: str,
    difficulty: int,
    function_name: str,
    specification: str,
    buggy_code: str,
    reference_code: str,
    tests: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "probe_id": probe_id,
        "workload_family": "fix_bug",
        "source_dataset": "Reproducible executable repair probes derived from public bug-fix task patterns",
        "difficulty": difficulty,
        "function_name": function_name,
        "prompt": (
            "Repair the Python function so it satisfies the specification and hidden unit tests. "
            "Return only one complete function definition. Do not use imports, type annotations, markdown, "
            "file access, network access, eval, or exec.\n\n"
            f"Specification: {specification}\n\nBuggy code:\n{buggy_code}"
        ),
        "validator_type": "safe_executable_unit_tests",
        "buggy_code": buggy_code,
        "reference_code": reference_code,
        "tests": tests,
    }


def build() -> list[dict[str, Any]]:
    return [
        probe(
            "CAL2-BUG-D1-01", 1, "count_even", "Return the number of even integers in values.",
            "def count_even(values):\n    return sum(1 for value in values if value % 2 == 1)",
            "def count_even(values):\n    return sum(1 for value in values if value % 2 == 0)",
            [{"args": [[1, 2, 3, 4]], "expected": 2}, {"args": [[]], "expected": 0}, {"args": [[2, 2, 5]], "expected": 2}],
        ),
        probe(
            "CAL2-BUG-D1-02", 1, "last_or_none", "Return the last item, or None for an empty list.",
            "def last_or_none(values):\n    if not values:\n        return None\n    return values[0]",
            "def last_or_none(values):\n    if not values:\n        return None\n    return values[-1]",
            [{"args": [[3, 4, 5]], "expected": 5}, {"args": [[]], "expected": None}, {"args": [[9]], "expected": 9}],
        ),
        probe(
            "CAL2-BUG-D1-03", 1, "safe_divide", "Return numerator/denominator, but return 0.0 when denominator is zero.",
            "def safe_divide(numerator, denominator):\n    if denominator < 0:\n        return 0.0\n    return numerator / denominator",
            "def safe_divide(numerator, denominator):\n    if denominator == 0:\n        return 0.0\n    return numerator / denominator",
            [{"args": [8, 2], "expected": 4.0}, {"args": [8, 0], "expected": 0.0}, {"args": [8, -2], "expected": -4.0}],
        ),
        probe(
            "CAL2-BUG-D1-04", 1, "clamp", "Clamp value into the inclusive interval [lower, upper].",
            "def clamp(value, lower, upper):\n    return min(lower, max(value, upper))",
            "def clamp(value, lower, upper):\n    return max(lower, min(value, upper))",
            [{"args": [5, 0, 10], "expected": 5}, {"args": [-2, 0, 10], "expected": 0}, {"args": [20, 0, 10], "expected": 10}],
        ),
        probe(
            "CAL2-BUG-D1-05", 1, "mean_or_zero", "Return the arithmetic mean, or 0.0 for an empty list.",
            "def mean_or_zero(values):\n    if not values:\n        return 0.0\n    return sum(values[:-1]) / len(values)",
            "def mean_or_zero(values):\n    if not values:\n        return 0.0\n    return sum(values) / len(values)",
            [{"args": [[2, 4, 6]], "expected": 4.0}, {"args": [[]], "expected": 0.0}, {"args": [[5]], "expected": 5.0}],
        ),
        probe(
            "CAL2-BUG-D2-01", 2, "dedupe_preserve_order", "Remove duplicates while preserving first-occurrence order.",
            "def dedupe_preserve_order(values):\n    return sorted(set(values))",
            "def dedupe_preserve_order(values):\n    seen = set()\n    result = []\n    for value in values:\n        if value not in seen:\n            seen.add(value)\n            result.append(value)\n    return result",
            [{"args": [[3, 1, 3, 2, 1]], "expected": [3, 1, 2]}, {"args": [[]], "expected": []}, {"args": [[2, 2, 2]], "expected": [2]}],
        ),
        probe(
            "CAL2-BUG-D2-02", 2, "moving_average", "Return all contiguous moving averages of the given positive window. Return [] if window is invalid or larger than values.",
            "def moving_average(values, window):\n    if window <= 0 or window > len(values):\n        return []\n    return [sum(values[i:i + window]) / window for i in range(len(values) - window)]",
            "def moving_average(values, window):\n    if window <= 0 or window > len(values):\n        return []\n    return [sum(values[i:i + window]) / window for i in range(len(values) - window + 1)]",
            [{"args": [[1, 2, 3, 4], 2], "expected": [1.5, 2.5, 3.5]}, {"args": [[1, 2], 2], "expected": [1.5]}, {"args": [[1], 2], "expected": []}],
        ),
        probe(
            "CAL2-BUG-D2-03", 2, "merge_counts", "Merge two count dictionaries by summing values for shared keys.",
            "def merge_counts(left, right):\n    result = dict(left)\n    for key, value in right.items():\n        result[key] = value\n    return result",
            "def merge_counts(left, right):\n    result = dict(left)\n    for key, value in right.items():\n        result[key] = result.get(key, 0) + value\n    return result",
            [{"args": [{"a": 2, "b": 1}, {"a": 3, "c": 4}], "expected": {"a": 5, "b": 1, "c": 4}}, {"args": [{}, {"x": 1}], "expected": {"x": 1}}],
        ),
        probe(
            "CAL2-BUG-D2-04", 2, "binary_search", "Return the index of target in sorted values, or -1 when absent.",
            "def binary_search(values, target):\n    low, high = 0, len(values)\n    while low <= high:\n        middle = (low + high) // 2\n        if values[middle] == target:\n            return middle\n        if values[middle] < target:\n            low = middle + 1\n        else:\n            high = middle - 1\n    return -1",
            "def binary_search(values, target):\n    low, high = 0, len(values) - 1\n    while low <= high:\n        middle = (low + high) // 2\n        if values[middle] == target:\n            return middle\n        if values[middle] < target:\n            low = middle + 1\n        else:\n            high = middle - 1\n    return -1",
            [{"args": [[1, 3, 5, 7], 5], "expected": 2}, {"args": [[1, 3, 5, 7], 8], "expected": -1}, {"args": [[], 1], "expected": -1}],
        ),
        probe(
            "CAL2-BUG-D2-05", 2, "minmax_scale", "Scale values to [0,1]. For a constant non-empty list return all zeros; for empty input return [].",
            "def minmax_scale(values):\n    if not values:\n        return []\n    low, high = min(values), max(values)\n    return [(value - low) / (high - low) for value in values]",
            "def minmax_scale(values):\n    if not values:\n        return []\n    low, high = min(values), max(values)\n    if high == low:\n        return [0.0 for value in values]\n    return [(value - low) / (high - low) for value in values]",
            [{"args": [[2, 4, 6]], "expected": [0.0, 0.5, 1.0]}, {"args": [[3, 3]], "expected": [0.0, 0.0]}, {"args": [[]], "expected": []}],
        ),
        probe(
            "CAL2-BUG-D3-01", 3, "longest_increasing_run", "Return the length of the longest strictly increasing contiguous run; return 0 for empty input.",
            "def longest_increasing_run(values):\n    if not values:\n        return 0\n    best = current = 1\n    for index in range(1, len(values)):\n        if values[index] >= values[index - 1]:\n            current += 1\n        else:\n            current = 1\n        best = max(best, current)\n    return best",
            "def longest_increasing_run(values):\n    if not values:\n        return 0\n    best = current = 1\n    for index in range(1, len(values)):\n        if values[index] > values[index - 1]:\n            current += 1\n        else:\n            current = 1\n        best = max(best, current)\n    return best",
            [{"args": [[1, 2, 2, 3, 4]], "expected": 3}, {"args": [[5, 4]], "expected": 1}, {"args": [[]], "expected": 0}],
        ),
        probe(
            "CAL2-BUG-D3-02", 3, "merge_intervals", "Merge sorted [start,end] intervals when they overlap or touch; return lists.",
            "def merge_intervals(intervals):\n    result = []\n    for start, end in intervals:\n        if not result or start >= result[-1][1]:\n            result.append([start, end])\n        else:\n            result[-1][1] = max(result[-1][1], end)\n    return result",
            "def merge_intervals(intervals):\n    result = []\n    for start, end in intervals:\n        if not result or start > result[-1][1]:\n            result.append([start, end])\n        else:\n            result[-1][1] = max(result[-1][1], end)\n    return result",
            [{"args": [[[1, 3], [3, 5], [8, 9]]], "expected": [[1, 5], [8, 9]]}, {"args": [[]], "expected": []}, {"args": [[[1, 4], [2, 3]]], "expected": [[1, 4]]}],
        ),
        probe(
            "CAL2-BUG-D3-03", 3, "top_k_frequent", "Return up to k values ordered by descending frequency, breaking ties by smaller value.",
            "def top_k_frequent(values, k):\n    counts = {}\n    for value in values:\n        counts[value] = counts.get(value, 0) + 1\n    return sorted(counts, key=counts.get, reverse=True)[:k]",
            "def top_k_frequent(values, k):\n    counts = {}\n    for value in values:\n        counts[value] = counts.get(value, 0) + 1\n    return sorted(counts, key=lambda value: (-counts[value], value))[:k]",
            [{"args": [[2, 1, 2, 1, 3], 2], "expected": [1, 2]}, {"args": [[4, 4, 2, 3, 3], 3], "expected": [3, 4, 2]}, {"args": [[], 2], "expected": []}],
        ),
        probe(
            "CAL2-BUG-D3-04", 3, "confusion_metrics", "Return precision, recall, and F1. Any metric with a zero denominator must be 0.0.",
            "def confusion_metrics(tp, fp, fn):\n    precision = tp / (tp + fp)\n    recall = tp / (tp + fn)\n    f1 = (precision + recall) / 2\n    return {'precision': precision, 'recall': recall, 'f1': f1}",
            "def confusion_metrics(tp, fp, fn):\n    precision = tp / (tp + fp) if tp + fp else 0.0\n    recall = tp / (tp + fn) if tp + fn else 0.0\n    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0\n    return {'precision': precision, 'recall': recall, 'f1': f1}",
            [{"args": [8, 2, 2], "expected": {"precision": 0.8, "recall": 0.8, "f1": 0.8}}, {"args": [0, 0, 0], "expected": {"precision": 0.0, "recall": 0.0, "f1": 0.0}}, {"args": [6, 2, 4], "expected": {"precision": 0.75, "recall": 0.6, "f1": 0.6666666666666666}}],
        ),
        probe(
            "CAL2-BUG-D3-05", 3, "select_threshold", "Each row is [threshold,tp,fp,fn]. Select the threshold with highest F1; ties choose the lower threshold. Return None for no rows.",
            "def select_threshold(rows):\n    if not rows:\n        return None\n    best_threshold, best_score = None, -1.0\n    for threshold, tp, fp, fn in rows:\n        precision = tp / (tp + fp) if tp + fp else 0.0\n        recall = tp / (tp + fn) if tp + fn else 0.0\n        score = precision + recall\n        if score > best_score:\n            best_threshold, best_score = threshold, score\n    return best_threshold",
            "def select_threshold(rows):\n    if not rows:\n        return None\n    best_threshold, best_score = None, -1.0\n    for threshold, tp, fp, fn in rows:\n        precision = tp / (tp + fp) if tp + fp else 0.0\n        recall = tp / (tp + fn) if tp + fn else 0.0\n        score = 2 * precision * recall / (precision + recall) if precision + recall else 0.0\n        if score > best_score or (score == best_score and threshold < best_threshold):\n            best_threshold, best_score = threshold, score\n    return best_threshold",
            [{"args": [[[0.3, 4, 0, 6], [0.5, 13, 7, 7]]], "expected": 0.5}, {"args": [[]], "expected": None}, {"args": [[[0.2, 4, 1, 1], [0.4, 4, 1, 1]]], "expected": 0.2}],
        ),
    ]


def run_worker(code: str, function_name: str, tests: list[dict[str, Any]]) -> bool:
    completed = subprocess.run(
        [sys.executable, "-I", "-S", str(WORKER)],
        input=json.dumps({"code": code, "function_name": function_name, "tests": tests}),
        text=True,
        capture_output=True,
        timeout=3,
        check=True,
    )
    return bool(json.loads(completed.stdout)["passed"])


def main() -> int:
    probes = build()
    for item in probes:
        if not run_worker(item["reference_code"], item["function_name"], item["tests"]):
            raise ValueError(f"reference failed: {item['probe_id']}")
        if run_worker(item["buggy_code"], item["function_name"], item["tests"]):
            raise ValueError(f"buggy code unexpectedly passed: {item['probe_id']}")
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as handle:
        for item in probes:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"output": str(OUTPUT), "probes": len(probes), "preflight": "all references pass; all buggy versions fail"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
