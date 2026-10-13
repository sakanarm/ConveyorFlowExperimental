from __future__ import annotations

import hashlib
import math


def _digest(seed: int, *parts: object) -> bytes:
    text = "|".join([str(seed), *(str(part) for part in parts)])
    return hashlib.sha256(text.encode("utf-8")).digest()


def uniform(seed: int, *parts: object) -> float:
    value = int.from_bytes(_digest(seed, *parts)[:8], "big")
    return (value + 0.5) / (2**64)


def normal(seed: int, *parts: object) -> float:
    u1 = max(1e-15, uniform(seed, *parts, "u1"))
    u2 = uniform(seed, *parts, "u2")
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def exponential(seed: int, mean: float, *parts: object) -> float:
    return -mean * math.log(max(1e-15, 1.0 - uniform(seed, *parts)))


def weighted_choice(seed: int, weights: dict[int, float], *parts: object) -> int:
    draw = uniform(seed, *parts)
    cumulative = 0.0
    last = next(iter(weights))
    for value, weight in sorted(weights.items()):
        last = value
        cumulative += weight
        if draw <= cumulative:
            return value
    return last


def stable_hex(*parts: object, length: int = 16) -> str:
    text = "|".join(str(part) for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]

