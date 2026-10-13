"""Measure a local-claim versus coordinator-relay IPC proxy on one host.

Both arms use the same claim-store process and payload. Central adds one relay
process; it cannot re-rank, change candidates, or bypass the store. This is a
prototype overhead measurement, not MFEC/provider latency or real outage data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing as mp
import random
import statistics
import time
from pathlib import Path
from queue import Empty


HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config_overhead_proxy_v1.json"
RESULTS = HERE / "results" / "overhead_proxy_v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def store_worker(store_in, local_out, coordinator_out) -> None:
    claimed = set()
    while True:
        message = store_in.get()
        if message is None:
            return
        route, request_id = message
        winner = request_id not in claimed
        if winner:
            claimed.add(request_id)
        (local_out if route == "local" else coordinator_out).put((request_id, winner))


def coordinator_worker(coordinator_in, store_in, coordinator_out, central_out,
                       timeout: int) -> None:
    while True:
        request_id = coordinator_in.get()
        if request_id is None:
            return
        store_in.put(("central", request_id))
        response = coordinator_out.get(timeout=timeout)
        central_out.put(response)


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def measure(*, seed: int, warmup_pairs: int, pairs: int, timeout: int) -> list[dict]:
    if pairs < 1 or warmup_pairs < 0:
        raise ValueError("invalid measurement count")
    context = mp.get_context("spawn")
    store_in = context.Queue()
    local_out = context.Queue()
    coordinator_out = context.Queue()
    coordinator_in = context.Queue()
    central_out = context.Queue()
    store = context.Process(target=store_worker,
                            args=(store_in, local_out, coordinator_out))
    coordinator = context.Process(target=coordinator_worker,
                                  args=(coordinator_in, store_in, coordinator_out,
                                        central_out, timeout))
    store.start()
    coordinator.start()
    rng = random.Random(seed)
    rows = []
    next_id = 0
    try:
        for pair_id in range(-warmup_pairs, pairs):
            order = ("local", "central") if rng.getrandbits(1) else ("central", "local")
            times = {}
            for route in order:
                request_id = next_id
                next_id += 1
                started = time.perf_counter_ns()
                if route == "local":
                    store_in.put(("local", request_id))
                    response = local_out.get(timeout=timeout)
                else:
                    coordinator_in.put(request_id)
                    response = central_out.get(timeout=timeout)
                elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
                if response != (request_id, True):
                    raise RuntimeError("claim-store response mismatch or unexpected collision")
                times[route] = elapsed_ms
            if pair_id >= 0:
                rows.append({
                    "pair_id": pair_id,
                    "first_route": order[0],
                    "local_ms": times["local"],
                    "central_ms": times["central"],
                    "central_minus_local_ms": times["central"] - times["local"],
                })
    except Empty as error:
        raise RuntimeError("IPC proxy timed out; no overhead result is valid") from error
    finally:
        coordinator_in.put(None)
        coordinator.join(timeout=timeout)
        store_in.put(None)
        store.join(timeout=timeout)
        for process in (coordinator, store):
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        for queue in (store_in, local_out, coordinator_out, coordinator_in, central_out):
            queue.close()
    return rows


def summarize(rows: list[dict], *, seed: int) -> dict:
    if not rows:
        raise ValueError("empty overhead measurement")
    local = [row["local_ms"] for row in rows]
    central = [row["central_ms"] for row in rows]
    difference = [row["central_minus_local_ms"] for row in rows]
    rng = random.Random(seed + 1)
    bootstrap = [statistics.mean(rng.choices(difference, k=len(difference)))
                 for _ in range(2000)]
    return {
        "status": "single_host_serial_ipc_proxy_measured",
        "not_provider_latency": True,
        "not_real_outage_evidence": True,
        "pairs": len(rows),
        "local_median_ms": statistics.median(local),
        "central_median_ms": statistics.median(central),
        "local_p95_ms": _percentile(local, 0.95),
        "central_p95_ms": _percentile(central, 0.95),
        "paired_mean_central_minus_local_ms": statistics.mean(difference),
        "paired_mean_difference_ci95_ms": [
            _percentile(bootstrap, 0.025), _percentile(bootstrap, 0.975)
        ],
        "negative_pair_differences": sum(value < 0 for value in difference),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if config["status"] != "frozen_before_measurement":
        raise ValueError("overhead proxy config is not frozen")
    output = RESULTS / ("smoke" if args.smoke else "main")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite prior overhead result: {output}")
    count = config["smoke_pairs"] if args.smoke else config["main_pairs"]
    rows = measure(seed=config["seed"], warmup_pairs=config["warmup_pairs"],
                   pairs=count, timeout=config["response_timeout_seconds"])
    analysis = summarize(rows, seed=config["seed"])
    output.mkdir(parents=True)
    csv_path = output / "paired_latency.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        **analysis,
        "research_results": not args.smoke,
        "interpretation": "measured local IPC proxy only; requires external-load validation before E1 use",
        "sha256": {
            "config": sha256(CONFIG), "runner": sha256(Path(__file__)),
            "paired_latency": sha256(csv_path),
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                                 encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
