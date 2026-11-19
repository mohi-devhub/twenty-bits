"""Compare guarded operations on disposable copies; never call a provider."""

import asyncio
from collections import Counter
import cProfile
import hashlib
import io
import json
import os
from pathlib import Path
import pstats
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.budget import Ledger
from twenty_bits.worlds import ROOT


def guarded_operation(ledger, index):
    operation = f"[offline-benchmark] sample-{index}"
    ledger.summary(operation_prefix="[offline-benchmark] ")
    callbacks = []

    def send():
        entries = ledger.entries(operation=operation, states={"dispatching"})
        assert len(entries) == 1
        ledger.attach_request_id(entries[0]["id"], f"fake:{index}")
        callbacks.append(True)
        return "fake-result"

    entry_id, result = ledger.call(
        send, phase=4, operation=operation, estimate_usd="0", max_cost_usd="0"
    )
    assert result == "fake-result" and callbacks == [True]
    assert ledger.get(entry_id)["request_id"] == f"fake:{index}"
    ledger.settle(entry_id, actual_usd="0", evidence="offline benchmark, no provider")
    return entry_id


async def loop_probe(ledger):
    ticks = []
    running = True

    async def heartbeat():
        while running:
            start = time.perf_counter()
            await asyncio.sleep(0.01)
            ticks.append(max(0, time.perf_counter() - start - 0.01))

    async def player(member):
        for index in range(10):
            guarded_operation(ledger, 1000 + 10 * member + index)
            await asyncio.sleep(0.001)

    task = asyncio.create_task(heartbeat())
    started = time.perf_counter()
    await asyncio.gather(*(player(member) for member in range(16)))
    running = False
    await task
    return {
        "concurrent_players": 16,
        "guarded_operations": 160,
        "seconds": time.perf_counter() - started,
        "maximum_event_loop_lag_seconds": max(ticks),
        "heartbeat_samples": len(ticks),
        "errors": 0,
    }


def main():
    source = ROOT / "ledger.json"
    before = source.read_bytes()
    original = json.loads(before)
    original.pop("storage", None)
    load_before = list(os.getloadavg())
    timings = {"json": [], "sqlite": []}
    with tempfile.TemporaryDirectory(prefix="twenty-bits-ledger-benchmark-") as tmp:
        copies = {}
        for backend in timings:
            path = Path(tmp) / backend / "ledger.json"
            path.parent.mkdir()
            path.write_text(json.dumps(original, indent=2) + "\n")
            copies[backend] = Ledger(path)
        copies["sqlite"].migrate()
        copies["sqlite"].summary()
        for trial in range(5):
            for backend in timings:
                start = time.perf_counter()
                guarded_operation(copies[backend], trial)
                elapsed = time.perf_counter() - start
                timings[backend].append(elapsed)
                print(
                    json.dumps(
                        {"trial": trial, "backend": backend, "seconds": elapsed}
                    ),
                    flush=True,
                )
        loop = asyncio.run(loop_probe(copies["sqlite"]))
        profiler = cProfile.Profile()
        profiler.runcall(guarded_operation, copies["sqlite"], 999)
        text = io.StringIO()
        pstats.Stats(profiler, stream=text).sort_stats("cumulative").print_stats(12)
        for backend, ledger in copies.items():
            current = ledger.status()
            assert current["entries"][: len(original["entries"])] == original["entries"]
            assert current["spent_usd"] == Ledger(source).summary()["spent_usd"]
            assert current["held_usd"] == Ledger(source).summary()["held_usd"]
            expected = 5 + (161 if backend == "sqlite" else 0)
            assert len(current["entries"]) == len(original["entries"]) + expected
    assert source.read_bytes() == before
    result = {
        "claim": "The migrated local guard avoids whole-history serialization; this is not an LLM throughput measurement.",
        "source_entries": len(original["entries"]),
        "source_bytes": len(before),
        "source_sha256": hashlib.sha256(before).hexdigest(),
        "load_average_before": load_before,
        "load_average_after": list(os.getloadavg()),
        "logical_cpus": os.cpu_count(),
        "service_calls": 0,
        "live_ledger_mutations": 0,
        "errors": 0,
        "trials": timings,
        "median_seconds": {k: statistics.median(v) for k, v in timings.items()},
        "range_seconds": {k: [min(v), max(v)] for k, v in timings.items()},
        "event_loop_probe": loop,
        "profile_separate_from_timing": text.getvalue(),
        "all_original_entries_unchanged": True,
        "limiter": "JSON baseline repeatedly validates and serializes the whole history. SQLite uses indexed reads, integer totals and durable small transactions; filesystem sync/transaction costs remain.",
        "execution_parallelism_safe_by_local_check": loop[
            "maximum_event_loop_lag_seconds"
        ]
        < 0.5,
        "limits": "Five alternating local-copy trials and a simulated 16-player event loop. No network, sampler, trainer or server throughput was measured. Future network failures still require draining and recovery.",
    }
    (ROOT / "research/ledger_performance_after_migration.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in ["profile_separate_from_timing", "trials"]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
