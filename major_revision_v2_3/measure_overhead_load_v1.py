"""Concurrent-load sensitivity for the direct-claim/coordinator-relay IPC proxy.

Each client has one outstanding claim at a time. Both routes use one claim
store; central adds one serial forwarding process. Sessions use new processes
and unique IDs. This is local prototype instrumentation, not provider latency.
"""

from __future__ import annotations

import csv
import hashlib
import json
import multiprocessing as mp
import random
import statistics
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config_overhead_load_v1.json"
RESULTS = HERE / "results" / "overhead_load_v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def claim_store(requests, relay_responses, client_responses) -> None:
    seen = set()
    while True:
        message = requests.get()
        if message is None:
            return
        route, request_id, client_id = message
        winner = request_id not in seen
        seen.add(request_id)
        response = (request_id, winner)
        if route == "central":
            relay_responses.put((client_id, response))
        else:
            client_responses[client_id].put(response)


def relay(central_requests, store_requests, relay_responses,
          client_responses, timeout: int) -> None:
    while True:
        message = central_requests.get()
        if message is None:
            return
        request_id, client_id = message
        store_requests.put(("central", request_id, client_id))
        response_client, response = relay_responses.get(timeout=timeout)
        if response_client != client_id:
            raise RuntimeError("relay response order changed")
        client_responses[client_id].put(response)


def client(client_id: int, route: str, repetition: int, warmup: int,
           count: int, barrier, store_requests, central_requests, response,
           results, timeout: int) -> None:
    try:
        latencies = []
        barrier.wait(timeout=timeout)
        for index in range(-warmup, count):
            request_id = (repetition, route, client_id, index)
            started = time.perf_counter_ns()
            if route == "local":
                store_requests.put((route, request_id, client_id))
            else:
                central_requests.put((request_id, client_id))
            reply = response.get(timeout=timeout)
            if reply != (request_id, True):
                raise RuntimeError("claim-store response mismatch")
            if index >= 0:
                latencies.append((time.perf_counter_ns() - started) / 1_000_000)
        results.put((client_id, latencies, None))
    except Exception as error:
        results.put((client_id, [], repr(error)))


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def session(*, clients: int, repetition: int, route: str, warmup: int,
            count: int, timeout: int) -> dict:
    context = mp.get_context("spawn")
    store_requests = context.Queue()
    central_requests = context.Queue()
    relay_responses = context.Queue()
    responses = [context.Queue() for _ in range(clients)]
    results = context.Queue()
    barrier = context.Barrier(clients)
    store = context.Process(target=claim_store,
                            args=(store_requests, relay_responses, responses))
    coordinator = context.Process(target=relay,
                                  args=(central_requests, store_requests,
                                        relay_responses, responses, timeout))
    workers = [context.Process(target=client,
                               args=(index, route, repetition, warmup, count,
                                     barrier, store_requests, central_requests,
                                     responses[index], results, timeout))
               for index in range(clients)]
    processes = [store, coordinator, *workers]
    for process in processes:
        process.start()
    try:
        observations = [results.get(timeout=timeout * 4) for _ in workers]
        for worker in workers:
            worker.join(timeout=timeout)
        if any(worker.is_alive() or worker.exitcode != 0 for worker in workers):
            raise RuntimeError("client process did not finish cleanly")
        errors = [error for _, _, error in observations if error]
        if errors:
            raise RuntimeError(f"client error: {errors[0]}")
        all_latencies = [value for _, values, _ in observations for value in values]
        if len(all_latencies) != clients * count:
            raise RuntimeError("measurement count mismatch")
        return {
            "clients": clients,
            "repetition": repetition,
            "route": route,
            "requests": len(all_latencies),
            "median_ms": statistics.median(all_latencies),
            "p95_ms": percentile(all_latencies, 0.95),
            "mean_ms": statistics.mean(all_latencies),
        }
    finally:
        central_requests.put(None)
        coordinator.join(timeout=timeout)
        store_requests.put(None)
        store.join(timeout=timeout)
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        for queue in [store_requests, central_requests, relay_responses,
                      results, *responses]:
            queue.close()


def summarize(rows: list[dict], config: dict) -> dict:
    summaries = []
    for clients in config["concurrent_clients"]:
        local = [row for row in rows if row["clients"] == clients
                 and row["route"] == "local"]
        central = [row for row in rows if row["clients"] == clients
                   and row["route"] == "central"]
        if len(local) != len(central) or len(local) != config["repetitions_per_level"]:
            raise ValueError("unbalanced load-sensitivity sessions")
        local.sort(key=lambda row: row["repetition"])
        central.sort(key=lambda row: row["repetition"])
        differences = [c["median_ms"] - l["median_ms"]
                       for l, c in zip(local, central)]
        summaries.append({
            "clients": clients,
            "session_pairs": len(differences),
            "local_median_of_session_medians_ms": statistics.median(
                row["median_ms"] for row in local),
            "central_median_of_session_medians_ms": statistics.median(
                row["median_ms"] for row in central),
            "median_paired_session_difference_ms": statistics.median(differences),
        })
    return {"status": "single_host_ipc_load_proxy_measured",
            "not_provider_latency": True,
            "not_real_outage_evidence": True,
            "sessions": len(rows),
            "load_levels": summaries}


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if config["status"] != "frozen_before_measurement":
        raise ValueError("load config is not frozen")
    output = RESULTS / "main"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite prior load result: {output}")
    rng = random.Random(config["seed"])
    rows = []
    for clients in config["concurrent_clients"]:
        for repetition in range(config["repetitions_per_level"]):
            order = ["local", "central"]
            rng.shuffle(order)
            for route in order:
                rows.append(session(
                    clients=clients, repetition=repetition, route=route,
                    warmup=config["warmup_requests_per_client"],
                    count=config["measured_requests_per_client"],
                    timeout=config["response_timeout_seconds"]))
    analysis = summarize(rows, config)
    output.mkdir(parents=True)
    csv_path = output / "sessions.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        **analysis,
        "research_results": True,
        "interpretation": "single-host IPC load proxy only; do not use as provider/network E1",
        "sha256": {"config": sha256(CONFIG), "runner": sha256(Path(__file__)),
                   "sessions": sha256(csv_path)},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                          encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
