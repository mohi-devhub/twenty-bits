"""Check immutable controls, financial invariants and offline replay artifacts."""

import asyncio
from contextlib import redirect_stdout
from decimal import Decimal
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts import run_visible_budget
from twenty_bits.budget import ACTIVE_STATES, Ledger
from twenty_bits.evaluation import frozen_games, frozen_manifest
from twenty_bits.recovery import RecoveringTransport
from twenty_bits.tinker_transport import save_json
from twenty_bits.worlds import ROOT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = ROOT / "results/visible_budget"
    summary = json.loads((out / "summary.json").read_text())
    complete = json.loads((out / "completion.json").read_text())
    proof = json.loads((ROOT / "research/visible_budget_preflight.json").read_text())
    assert complete["all_HTTP_work_drained"] and complete["ledger_export_complete"]
    assert complete["games"] == 840 and summary["training_games"] == 0
    assert summary["verification"]["training_calls"] == 0
    for name, digest in proof["immutable_sha256"].items():
        assert sha(ROOT / name) == digest, name
    expected = {
        r["id"]: r
        for cell in frozen_manifest()["cells"]
        for r in frozen_games(cell["domain"], cell["n"], cell["noise"], 28)
    }
    records = json.loads(
        gzip.decompress(
            (ROOT / "experiments/visible_budget_games.json.gz").read_bytes()
        )
    )
    assert expected == {r["id"]: r for r in records}
    config = json.loads((ROOT / "experiments/visible_budget.json").read_text())
    for old_name in ["main_A11", "main_A23", "main_B41"]:
        old_config = json.loads((ROOT / f"experiments/{old_name}.json").read_text())
        for key in [
            "primary_model",
            "primary_thinking",
            "primary_output_cap",
            "context_window",
            "temperature",
            "top_p",
            "top_k",
            "grammar_version",
            "posterior_threshold",
            "reward",
        ]:
            assert old_config[key] == config[key], (old_name, key)
    snapshot = Ledger.read_snapshot(ROOT / "ledger.json")
    status = Ledger.snapshot_status(ROOT / "ledger.json")
    assert Decimal(status["spent_usd"]) + Decimal(status["held_usd"]) <= Decimal("50")
    previous = {}
    old = json.loads((ROOT / "research/ledger_events_archive.json").read_text())
    assert sha(ROOT / old["archive"]) == old["archive_sha256"]
    for line in gzip.open(ROOT / old["archive"], "rt"):
        row = json.loads(line)
        previous[row["entry_id"]] = row["entry"]
    current = {e["id"]: e for e in snapshot["entries"]}
    assert all(current[key] == value for key, value in previous.items())
    new = [e for key, e in current.items() if key not in previous]
    assert all(e["operation"].startswith("[visible-budget-v1] ") for e in new)
    registry = json.loads(
        (ROOT / "research/visible_budget_replacements.json").read_text()
    )
    lost_ids = set(registry["legacy_lost_entry_ids"]) | {
        c["original_entry_id"] for c in registry["cases"]
    }
    lost_exposure = sum(
        Decimal(current[key]["reserved_usd"])
        for key in lost_ids
        if current[key]["state"] in ACTIVE_STATES
    )
    assert lost_exposure < Decimal("0.50")
    financial = json.loads(
        (ROOT / "research/visible_budget_ledger_archive.json").read_text()
    )
    assert sha(ROOT / "ledger.json") == financial["ledger_json_sha256"]
    assert sha(ROOT / financial["archive"]) == financial["archive_sha256"]
    latest = {}
    totals = {}
    peak = Decimal(0)
    exposure = Decimal(0)
    for number, line in enumerate(gzip.open(ROOT / financial["archive"], "rt"), 1):
        row = json.loads(line)
        assert row["sequence"] == number
        entry = row["entry"]
        assert entry["id"] == row["entry_id"]
        latest[entry["id"]] = entry
        if entry["operation"].startswith("[visible-budget-v1] "):
            old_amount = totals.get(entry["id"], Decimal(0))
            amount = Decimal(entry.get("actual_usd") or "0")
            if entry["state"] in ACTIVE_STATES:
                amount += Decimal(entry["reserved_usd"])
            totals[entry["id"]] = amount
            exposure += amount - old_amount
            peak = max(peak, exposure)
            assert exposure <= Decimal("8")
    assert number == financial["events"]
    assert list(latest.values()) == snapshot["entries"]
    assert exposure == Decimal(summary["followup_budget"]["spent_usd"]) + Decimal(
        summary["followup_budget"]["held_usd"]
    )
    with patch.object(
        RecoveringTransport,
        "open",
        side_effect=AssertionError("No SDK access after the gate."),
    ):
        with redirect_stdout(io.StringIO()):
            asyncio.run(run_visible_budget.main())
    unit_log = (out / "unit_tests.log").read_text()
    assert "Ran 226 tests" in unit_log and unit_log.rstrip().endswith("OK")
    report = {
        "service_calls": 0,
        "unit_tests": 226,
        "primary_artifact_hashes_verified": len(proof["immutable_sha256"]),
        "same_frozen_games": 280,
        "followup_games": 840,
        "old_ledger_entries_unchanged": len(previous),
        "all_new_operations_within_followup": True,
        "new_ledger_entries": len(new),
        "append_only_ledger_events_verified": financial["events"],
        "followup_peak_spent_plus_holds_usd": str(peak),
        "lost_originals": len(lost_ids),
        "lost_original_holds_usd": str(lost_exposure),
        "completed_runner_returns_before_SDK": True,
        "new_training_calls": 0,
        "project_spent_usd": status["spent_usd"],
        "project_held_usd": status["held_usd"],
        "project_available_usd": status["available_usd"],
    }
    save_json(out / "validation.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
