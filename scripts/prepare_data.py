from __future__ import annotations

import csv
import io
import json
import statistics
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DERIVED = ROOT / "data" / "derived"
OUTPUT = DERIVED / "corpus_profiles.json"


def quantiles(values: list[int]) -> dict[str, float]:
    ordered = sorted(values)
    def pick(q: float) -> float:
        if not ordered:
            return 0.0
        return float(ordered[min(len(ordered) - 1, int(q * (len(ordered) - 1)))])
    return {"p25": pick(0.25), "p50": pick(0.50), "p75": pick(0.75), "p95": pick(0.95)}


def adult_profile() -> dict:
    rows = 0
    missing = 0
    cells = 0
    positive = 0
    with zipfile.ZipFile(RAW / "adult.zip") as archive:
        for name in archive.namelist():
            lower = name.lower()
            if not (lower.endswith("adult.data") or lower.endswith("adult.test")):
                continue
            text = archive.read(name).decode("utf-8", errors="replace").splitlines()
            for line in text:
                line = line.strip()
                if not line or line.startswith("|"):
                    continue
                values = [value.strip() for value in line.rstrip(".").split(",")]
                if len(values) != 15:
                    continue
                rows += 1
                cells += len(values)
                missing += sum(value == "?" for value in values)
                positive += int(values[-1].startswith(">50K"))
    return {
        "records": rows,
        "missing_fraction": missing / max(1, cells),
        "positive_fraction": positive / max(1, rows),
        "difficulty_weights": {"1": 0.45, "2": 0.40, "3": 0.15},
    }


def beijing_profile() -> dict:
    rows = 0
    missing = 0
    cells = 0
    stations: set[str] = set()
    def consume_csv(data: bytes) -> None:
        nonlocal rows, missing, cells
        lines = data.decode("utf-8-sig", errors="replace").splitlines()
        reader = csv.DictReader(lines)
        for row in reader:
            rows += 1
            values = list(row.values())
            cells += len(values)
            missing += sum(value in (None, "", "NA") for value in values)
            station = row.get("station")
            if station:
                stations.add(station)

    with zipfile.ZipFile(RAW / "beijing.zip") as archive:
        nested = next((name for name in archive.namelist() if name.lower().endswith(".zip")), None)
        if nested:
            with zipfile.ZipFile(io.BytesIO(archive.read(nested))) as inner:
                for name in inner.namelist():
                    if name.lower().endswith(".csv"):
                        consume_csv(inner.read(name))
        else:
            for name in archive.namelist():
                if name.lower().endswith(".csv") and name.lower() not in ("data.csv", "test.csv"):
                    consume_csv(archive.read(name))
    return {
        "records": rows,
        "stations": len(stations),
        "missing_fraction": missing / max(1, cells),
        "difficulty_weights": {"1": 0.30, "2": 0.45, "3": 0.25},
    }


def bugs_profile() -> dict:
    buggy_path = RAW / "bugs2fix" / "train.buggy.txt"
    fixed_path = RAW / "bugs2fix" / "train.fixed.txt"
    lengths: list[int] = []
    deltas: list[int] = []
    unequal = 0
    with buggy_path.open(encoding="utf-8", errors="replace") as buggy, fixed_path.open(
        encoding="utf-8", errors="replace"
    ) as fixed:
        for before, after in zip(buggy, fixed):
            before = before.rstrip("\n")
            after = after.rstrip("\n")
            lengths.append(len(before))
            deltas.append(abs(len(after) - len(before)))
            unequal += int(before != after)
    return {
        "records": len(lengths),
        "unequal_fraction": unequal / max(1, len(lengths)),
        "source_length": quantiles(lengths),
        "absolute_length_delta": quantiles(deltas),
        "mean_source_length": statistics.fmean(lengths) if lengths else 0.0,
        "difficulty_weights": {"1": 0.35, "2": 0.45, "3": 0.20},
        "execution_note": "Normalized function pairs; not executable repository tests.",
    }


def main() -> None:
    DERIVED.mkdir(parents=True, exist_ok=True)
    profiles = {
        "adult_ml": adult_profile(),
        "beijing_ml": beijing_profile(),
        "bugs2fix": bugs_profile(),
    }
    OUTPUT.write_text(json.dumps(profiles, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, profile in profiles.items():
        print(f"{name}: {profile['records']:,} records")


if __name__ == "__main__":
    main()
