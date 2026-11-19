"""Measure the existing guard on a disposable copy, without service calls."""

import cProfile
import hashlib
import io
import json
from pathlib import Path
import pstats
import statistics
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.budget import Ledger
from twenty_bits.worlds import ROOT


def guarded_operation(ledger, index):
    operation = f"offline ledger I/O diagnostic {index}"
    started = time.perf_counter()
    ledger.status()  # The transport's separate run-cap admission read.

    def send():
        matches = [e for e in ledger.status()["entries"]
                   if e["operation"] == operation and e["state"] == "dispatching"]
        assert len(matches) == 1
        ledger.attach_request_id(matches[0]["id"], f"offline-only:{index}")
        return "No network call"

    entry, result = ledger.call(send, phase=4, operation=operation,
                               estimate_usd="0", max_cost_usd="0")
    submitted = time.perf_counter()
    assert result == "No network call"
    ledger.settle(entry, actual_usd="0", evidence="Disposable local diagnostic only")
    finished = time.perf_counter()
    return {"durable_admission_and_ID_seconds": submitted-started,
            "settlement_seconds": finished-submitted,
            "total_blocking_seconds": finished-started}


def main():
    snapshot = (ROOT / "ledger.json").read_bytes()
    original = json.loads(snapshot)
    rows = []
    with tempfile.TemporaryDirectory(prefix="twenty-bits-ledger-diagnostic-") as directory:
        path = Path(directory) / "ledger.json"
        assert path.resolve() != (ROOT / "ledger.json").resolve()
        path.write_bytes(snapshot)
        ledger = Ledger(path)
        for index in range(5):
            rows.append(guarded_operation(ledger, index))
        profiler = cProfile.Profile()
        profiler.runcall(guarded_operation, ledger, 5)
        stream = io.StringIO()
        pstats.Stats(profiler, stream=stream).sort_stats("cumulative").print_stats(18)
        final = json.loads(path.read_text())
        assert final["entries"][:len(original["entries"])] == original["entries"]
        assert final["approvals"] == original["approvals"]
        assert len(final["entries"]) == len(original["entries"]) + 6
        assert all(e["actual_usd"] == "0.000000" and e["state"] == "settled"
                   for e in final["entries"][len(original["entries"]):])
    output = {"claim_tested": "The existing synchronous guard blocks the collector event loop for seconds at the current ledger size.",
        "source_ledger_bytes": len(snapshot),
        "source_snapshot_sha256": hashlib.sha256(snapshot).hexdigest(),
        "source_entries": len(original["entries"]), "service_calls": 0,
        "live_ledger_mutations": 0, "unprofiled_runs": rows,
        "median_seconds": {key: statistics.median(r[key] for r in rows) for key in rows[0]},
        "range_seconds": {key: [min(r[key] for r in rows), max(r[key] for r in rows)] for key in rows[0]},
        "profile_is_separate_from_reported_timings": True,
        "profile": stream.getvalue(),
        "limits": "Copied ledger on the same busy laptop while the paid collector continues. This isolates guard CPU/file work, not network latency, and is not an end-to-end speedup claim."}
    destination = ROOT / "research/A23_ledger_io_diagnostic.json"
    destination.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({key: value for key, value in output.items() if key != "profile"}, indent=2))


if __name__ == "__main__":
    main()
