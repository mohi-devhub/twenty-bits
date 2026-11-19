"""Export the drained follow-up's ledger without replacing prior gate archives."""

from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.budget import ACTIVE_STATES, Ledger
from twenty_bits.tinker_transport import save_json
from twenty_bits.worlds import ROOT


def main():
    out = ROOT / "results/visible_budget"
    complete = json.loads((out / "completion.json").read_text())
    config = json.loads((ROOT / "experiments/visible_budget.json").read_text())
    directory = ROOT / "runs" / config["run_id"]
    session = json.loads((directory / "sessions.json").read_text())
    assert complete["games"] == 840 and session["finished"]
    requests = [
        json.loads(p.read_text()) for p in (directory / "requests").glob("*.json")
    ]
    assert all(
        r.get("settled") or r.get("orphaned") or r.get("output_allowed") is False
        for r in requests
    )
    ledger = Ledger(ROOT / "ledger.json")
    run = ledger.summary(operation_prefix=f"[{config['run_id']}] ")
    assert Decimal(run["spent_usd"]) + Decimal(run["held_usd"]) <= Decimal("8")
    status = ledger.status()
    registry = json.loads(
        (ROOT / "research/visible_budget_replacements.json").read_text()
    )
    excluded_ids = {case["original_entry_id"] for case in registry["cases"]}
    run_entries = ledger.entries(operation_prefix=f"[{config['run_id']}] ")
    assert all(
        e["id"] in excluded_ids for e in run_entries if e["state"] in ACTIVE_STATES
    )
    ledger.export_snapshot()
    snapshot = Ledger.read_snapshot(ROOT / "ledger.json")
    assert status["entries"] == snapshot["entries"]
    archive = out / "ledger_events.jsonl.gz"
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
                compressed.write(
                    (
                        json.dumps(
                            {
                                "sequence": sequence,
                                "entry_id": entry_id,
                                "entry": entry,
                            },
                            separators=(",", ":"),
                        )
                        + "\n"
                    ).encode()
                )
    assert list(latest.values()) == snapshot["entries"]
    save_json(
        ROOT / "research/visible_budget_ledger_archive.json",
        {
            "service_calls": 0,
            "events": count,
            "entries": len(latest),
            "latest_records_equal_completed_export": True,
            "ledger_json_sha256": hashlib.sha256(
                (ROOT / "ledger.json").read_bytes()
            ).hexdigest(),
            "archive": str(archive.relative_to(ROOT)),
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "prior_B41_archive_untouched": True,
            "all_HTTP_work_drained": True,
        },
    )
    save_json(out / "sessions.json", session)
    complete.update(
        project_budget=ledger.summary(),
        run_budget={k: run[k] for k in ["spent_usd", "held_usd"]},
        all_HTTP_work_drained=True,
        ledger_export_complete=True,
    )
    save_json(out / "completion.json", complete)
    print(
        json.dumps(
            {
                "project": complete["project_budget"],
                "followup": complete["run_budget"],
                "events": count,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
