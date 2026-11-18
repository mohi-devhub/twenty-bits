"""Measure local collection delays without inferring the server's expiry time."""

from datetime import datetime
import gzip
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.worlds import ROOT


def main():
    directory = ROOT / "results/learnability_probe"
    incident = json.loads(
        (ROOT / "research/learnability_probe_incident.json").read_text()
    )
    entries = json.loads((ROOT / "ledger.json").read_text())["entries"]
    usage = [
        json.loads(line)
        for line in (directory / "usage.jsonl").read_text().splitlines()
    ]
    journals = {
        r["request_id"]: r
        for line in gzip.open(directory / "requests.jsonl.gz", "rt")
        if (r := json.loads(line)).get("request_id")
    }
    rows = []
    for turn in incident["turns"]:
        request_id = turn["request_id"]
        saved = journals[request_id]["saved_before_dispatch_at"]
        poll_entries = [
            e for e in entries if e["operation"].endswith("retrieve " + request_id)
        ]
        initial = min((e["created_at"] for e in poll_entries), default=None)
        terminal = min(
            (
                r["recorded_at"]
                for r in usage
                if r["operation"] == "retrieve " + request_id
                and r.get("pending") is False
                and not r.get("error_type")
            ),
            default=None,
        )
        inspected = next(
            (
                r["recorded_at"]
                for r in usage
                if r["operation"] == "inspect saved future " + request_id
            ),
            None,
        )

        def age(timestamp):
            return (
                (
                    datetime.fromisoformat(timestamp) - datetime.fromisoformat(saved)
                ).total_seconds()
                if timestamp
                else None
            )

        rows.append(
            {
                "request_id": request_id,
                "receipt_saved": turn["receipt_saved"],
                "saved_before_dispatch_at": saved,
                "first_collection_attempt_at": initial,
                "seconds_to_first_collection_attempt": age(initial),
                "earliest_terminal_recovery_reply_at": terminal,
                "seconds_to_earliest_terminal_recovery_reply": age(terminal),
                "explicit_inspection_at": inspected,
                "seconds_to_explicit_inspection": age(inspected),
                "inspection_result": turn["result"],
            }
        )
    result = {
        "basis": "Local fsynced journal and guarded operation timestamps, UTC. Server completion and expiry timestamps are not exposed; these ages measure observation latency, not the exact server retention time. Receipt-less requests also have unknown acceptance time.",
        "futures": rows,
    }
    (directory / "recovery_timing.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Measured four saved futures. No service calls.")


if __name__ == "__main__":
    main()
