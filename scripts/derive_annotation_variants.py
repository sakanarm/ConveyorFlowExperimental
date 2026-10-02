from __future__ import annotations

import csv
import hashlib
import io
import json
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUTPUT = ROOT / "data" / "derived" / "annotation_variants.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cut_points(values: list[int]) -> list[int]:
    ordered = sorted(values)
    return [ordered[int((len(ordered) - 1) * q)] for q in (0.25, 0.50, 0.75)]


def bin_index(value: int, cuts: list[int]) -> int:
    return sum(value > cut for cut in cuts)


def adult_variants() -> list[dict]:
    records: list[list[str]] = []
    with zipfile.ZipFile(RAW / "adult.zip") as archive:
        for name in ("adult.data", "adult.test"):
            for line in archive.read(name).decode("utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("|"):
                    continue
                row = [value.strip() for value in line.rstrip(".").split(",")]
                if len(row) == 15:
                    records.append(row)
    age_cuts = cut_points([int(row[0]) for row in records])
    hours_cuts = cut_points([int(row[12]) for row in records])
    groups: dict[tuple[int, int], list[list[str]]] = defaultdict(list)
    for row in records:
        groups[(bin_index(int(row[0]), age_cuts), bin_index(int(row[12]), hours_cuts))].append(row)
    variants = []
    for age_bin in range(4):
        for hours_bin in range(4):
            rows = groups[(age_bin, hours_bin)]
            cells = max(1, len(rows) * 15)
            missing = sum(value == "?" for row in rows for value in row)
            positive = sum(row[-1].startswith(">50K") for row in rows)
            variants.append(
                {
                    "variant": age_bin * 4 + hours_bin,
                    "stratum": f"age_q{age_bin + 1}_hours_q{hours_bin + 1}",
                    "records": len(rows),
                    "age_band": age_bin + 1,
                    "hours_per_week_band": hours_bin + 1,
                    "missing_fraction": round(missing / cells, 6),
                    "positive_fraction": round(positive / max(1, len(rows)), 6),
                    "description": "Adult classification subgroup defined by empirical age and weekly-hours quartiles.",
                }
            )
    return variants


def beijing_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with zipfile.ZipFile(RAW / "beijing.zip") as outer:
        nested_name = next(name for name in outer.namelist() if name.lower().endswith(".zip"))
        with zipfile.ZipFile(io.BytesIO(outer.read(nested_name))) as inner:
            for name in sorted(inner.namelist()):
                if not name.lower().endswith(".csv"):
                    continue
                text = inner.read(name).decode("utf-8-sig", errors="replace").splitlines()
                rows.extend(csv.DictReader(text))
    return rows


def summarize_beijing(rows: list[dict[str, str]], *, stratum: str, scope: str) -> dict:
    pollutant = ("PM2.5", "PM10", "SO2", "NO2", "CO", "O3")
    pollutant_cells = [row.get(key, "") for row in rows for key in pollutant]
    missing = sum(value in (None, "", "NA") for value in pollutant_cells)
    pm25 = [float(row["PM2.5"]) for row in rows if row.get("PM2.5") not in (None, "", "NA")]
    return {
        "stratum": stratum,
        "scope": scope,
        "records": len(rows),
        "stations": len({row.get("station", "") for row in rows}),
        "missing_pollutant_fraction": round(missing / max(1, len(pollutant_cells)), 6),
        "pm25_median": round(statistics.median(pm25), 3) if pm25 else None,
        "description": "Beijing air-quality regression/time-series stratum with chronological validation required.",
    }


def beijing_variants() -> list[dict]:
    rows = beijing_rows()
    stations = sorted({row["station"] for row in rows})
    variants = []
    for index, station in enumerate(stations):
        selected = [row for row in rows if row["station"] == station]
        variants.append(
            {
                "variant": index,
                **summarize_beijing(selected, stratum=f"station_{station}", scope="single_station"),
            }
        )
    for season in range(1, 5):
        months = {season * 3 - 2, season * 3 - 1, season * 3}
        selected = [row for row in rows if int(row["month"]) in months]
        variants.append(
            {
                "variant": len(stations) + season - 1,
                **summarize_beijing(
                    selected,
                    stratum=f"all_stations_months_{min(months):02d}_{max(months):02d}",
                    scope="multi_station_season",
                ),
            }
        )
    if len(variants) != 16:
        raise ValueError(f"expected 16 Beijing variants, found {len(variants)}")
    return variants


def bugs_variants() -> list[dict]:
    pairs = []
    buggy_path = RAW / "bugs2fix" / "train.buggy.txt"
    fixed_path = RAW / "bugs2fix" / "train.fixed.txt"
    with buggy_path.open(encoding="utf-8", errors="replace") as buggy, fixed_path.open(
        encoding="utf-8", errors="replace"
    ) as fixed:
        for before, after in zip(buggy, fixed):
            before, after = before.rstrip("\n"), after.rstrip("\n")
            pairs.append((len(before), abs(len(after) - len(before))))
    length_cuts = cut_points([value[0] for value in pairs])
    delta_cuts = cut_points([value[1] for value in pairs])
    groups: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for length, delta in pairs:
        groups[(bin_index(length, length_cuts), bin_index(delta, delta_cuts))].append((length, delta))
    variants = []
    for length_bin in range(4):
        for delta_bin in range(4):
            rows = groups[(length_bin, delta_bin)]
            variants.append(
                {
                    "variant": length_bin * 4 + delta_bin,
                    "stratum": f"source_length_q{length_bin + 1}_patch_delta_q{delta_bin + 1}",
                    "records": len(rows),
                    "source_length_band": length_bin + 1,
                    "patch_delta_band": delta_bin + 1,
                    "median_source_characters": round(statistics.median(v[0] for v in rows), 3),
                    "median_absolute_length_delta": round(statistics.median(v[1] for v in rows), 3),
                    "description": "Normalized Java before/after function-pair stratum; no executable repository tests are available.",
                }
            )
    return variants


def main() -> int:
    manifest = ROOT / "data" / "manifest.json"
    result = {
        "schema_version": "2.0",
        "derivation": "Deterministic 16-stratum descriptors from each downloaded public corpus.",
        "source_manifest_sha256": sha256(manifest),
        "variants": {
            "adult_ml": adult_variants(),
            "beijing_ml": beijing_variants(),
            "bugs2fix": bugs_variants(),
        },
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {sum(len(v) for v in result['variants'].values())} variants to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
