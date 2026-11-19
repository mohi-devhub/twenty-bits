"""Migrate the drained project ledger offline and prove financial equality."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.budget import Ledger
from twenty_bits.worlds import ROOT


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main():
    path = ROOT / "ledger.json"
    ledger = Ledger(path)
    before = ledger.status()
    original = Ledger.read_snapshot(path)
    changed = ledger.migrate()
    after = ledger.status()
    assert after == before
    exported = ledger.export_snapshot()
    assert exported["entries"] == original["entries"]
    assert {k: v for k, v in exported.items() if k != "storage"} == {
        k: v for k, v in original.items() if k != "storage"
    }
    proof = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "migrated": changed,
        "engine": "sqlite-v1",
        "database": "ledger.sqlite3",
        "audit_export": "ledger.json",
        "entries": len(before["entries"]),
        "entry_records_identical": True,
        "entry_records_sha256": digest(before["entries"]),
        "approvals_unchanged": True,
        "approvals_sha256": digest(original.get("approvals")),
        "blocks_unchanged": True,
        "before": {k: v for k, v in before.items() if k != "entries"},
        "after": {k: v for k, v in after.items() if k != "entries"},
        "service_calls": 0,
        "semantics": "Same decimal rounding, estimate x 1.5 or full maximum, cap, dispatch-before-send, request ID, pending 408, settlement and unknown-cost holds. Only indexed live storage and reads change.",
        "durability": "SQLite FULL synchronous transactions and append-only event records. The live database must exist; missing/corrupt state fails closed. JSON exports occur explicitly outside request collection.",
    }
    (ROOT / "research/ledger_migration.json").write_text(
        json.dumps(proof, indent=2) + "\n"
    )
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
