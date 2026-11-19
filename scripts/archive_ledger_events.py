"""Archive the append-only live ledger history after B41 has drained HTTP."""

import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.budget import Ledger
from twenty_bits.worlds import ROOT


def main():
    completion = json.loads((ROOT / "results/main_B41/completion.json").read_text())
    assert completion["ledger_export_complete"] and completion["all_HTTP_work_drained"]
    ledger = Ledger(ROOT / "ledger.json")
    snapshot = Ledger.read_snapshot(ROOT / "ledger.json")
    archive = ROOT / "results/ledger_migration/events_through_B41.jsonl.gz"
    archive.parent.mkdir(exist_ok=True)
    latest = {}
    count = 0
    with ledger._locked(), ledger._database.transaction() as (connection, _):
        with (
            archive.open("wb") as raw,
            gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed,
        ):
            for sequence, entry_id, body in connection.execute(
                "SELECT sequence,entry_id,data FROM events ORDER BY sequence"
            ):
                count += 1
                assert sequence == count
                entry = json.loads(body)
                assert entry["id"] == entry_id
                latest[entry_id] = entry
                row = {"sequence": sequence, "entry_id": entry_id, "entry": entry}
                compressed.write(
                    (
                        json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n"
                    ).encode()
                )
        assert list(latest.values()) == snapshot["entries"]
    result = {
        "service_calls": 0,
        "events": count,
        "entries": len(latest),
        "latest_records_equal_completed_export": True,
        "ledger_json_sha256": hashlib.sha256(
            (ROOT / "ledger.json").read_bytes()
        ).hexdigest(),
        "archive": str(archive.relative_to(ROOT)),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_bytes": archive.stat().st_size,
        "note": "The initial imported snapshot contributes one event per existing entry. Later events preserve every transactional post-state. This archive is for offline audit; it is not permission to reconstruct a lost active ledger and resume spending.",
    }
    (ROOT / "research/ledger_events_archive.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
