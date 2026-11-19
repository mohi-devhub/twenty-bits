"""The existing budget contract also runs against migrated SQLite ledgers."""

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3
import unittest

import test_budget as contract
from twenty_bits.budget import BudgetError, Ledger


class SQLiteBudgetTests(contract.BudgetTests):
    def setUp(self):
        super().setUp()
        self.ledger.migrate()

    def reserve(self, estimate="1", maximum="1"):
        entry_id = super().reserve(estimate, maximum)
        # Two inherited tests deliberately edit the JSON audit export.
        self.ledger.export_snapshot()
        return entry_id


class MigrationTests(unittest.TestCase):
    setUp = contract.BudgetTests.setUp
    reserve = contract.BudgetTests.reserve

    def test_full_project_migration_preserves_every_entry_and_total(self):
        project = Path(__file__).resolve().parent.parent / "ledger.json"
        data = json.loads(project.read_text())
        data.pop("storage", None)
        self.path.write_text(json.dumps(data))
        ledger = Ledger(self.path)
        before = ledger.status()
        self.assertTrue(ledger.migrate())
        self.assertEqual(ledger.status(), before)
        self.assertEqual(Ledger(self.path).status(), before)
        self.assertFalse(ledger.migrate())
        exported = ledger.export_snapshot()
        self.assertEqual(exported["entries"], data["entries"])
        self.assertEqual(exported.get("approvals"), data.get("approvals"))
        self.assertEqual(exported["blocks"], data["blocks"])
        with sqlite3.connect(self.path.with_suffix(".sqlite3")) as connection:
            self.assertEqual(
                connection.execute("PRAGMA integrity_check").fetchone()[0], "ok"
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM entries").fetchone()[0],
                len(data["entries"]),
            )

    def test_database_loss_fails_closed_instead_of_using_stale_export(self):
        self.ledger.migrate()
        self.ledger.reserve(
            phase=2, operation="held", estimate_usd="1", max_cost_usd="1"
        )
        self.path.with_suffix(".sqlite3").unlink()
        with self.assertRaises(BudgetError):
            Ledger(self.path).call(
                lambda: self.fail("Missing ledger reached provider"),
                phase=2,
                operation="blocked",
                estimate_usd="0",
                max_cost_usd="0",
            )

    def test_sqlite_read_filters_and_summary_match_complete_status(self):
        self.ledger.migrate()
        a = self.ledger.reserve(
            phase=2, operation="[run] sample", estimate_usd="1", max_cost_usd="1"
        )
        self.ledger.reserve(
            phase=2, operation="[other] sample", estimate_usd="2", max_cost_usd="2"
        )
        self.ledger.dispatch(a, lambda: None)
        self.ledger.attach_request_id(a, "saved-id")
        self.assertEqual(self.ledger.get(a)["request_id"], "saved-id")
        self.assertEqual(
            self.ledger.entries(operation="[run] sample", states={"submitted"}),
            [self.ledger.get(a)],
        )
        self.assertEqual(
            self.ledger.summary(operation_prefix="[run] ")["held_usd"], "1.500000"
        )
        self.assertEqual(
            self.ledger.summary(),
            {k: v for k, v in self.ledger.status().items() if k != "entries"},
        )

    def test_transactions_roll_back_edits_that_raise(self):
        self.ledger.migrate()
        a = self.reserve()
        before = self.ledger.status()

        def edit(entry):
            entry["reserved_usd"] = "0.000000"
            raise ValueError("abort before commit")

        with self.assertRaises(ValueError):
            self.ledger._update(a, edit)
        self.assertEqual(self.ledger.status(), before)

    def test_migration_interruption_cannot_resume_on_stale_json(self):
        from unittest.mock import patch

        with patch.object(
            self.ledger, "_write", side_effect=OSError("interrupted switch")
        ):
            with self.assertRaises(OSError):
                self.ledger.migrate()
        with self.assertRaises(BudgetError):
            Ledger(self.path)

    def test_invalid_database_metadata_blocks_dispatch(self):
        self.ledger.migrate()
        with sqlite3.connect(self.path.with_suffix(".sqlite3")) as connection:
            meta = json.loads(
                connection.execute("SELECT data FROM metadata WHERE id=1").fetchone()[0]
            )
            meta["schema_version"] = 2
            connection.execute(
                "UPDATE metadata SET data=? WHERE id=1", (json.dumps(meta),)
            )
        with self.assertRaises(BudgetError):
            self.ledger.call(
                lambda: self.fail("Invalid metadata reached provider"),
                phase=2,
                operation="blocked",
                estimate_usd="0",
                max_cost_usd="0",
            )

    def test_export_is_an_offline_view_and_sqlite_keeps_append_history(self):
        self.ledger.migrate()
        a = self.ledger.reserve(
            phase=2, operation="sample", estimate_usd="1", max_cost_usd="1"
        )
        self.ledger.dispatch(a, lambda: None)
        self.ledger.attach_request_id(a, "original")
        self.ledger.settle(a, actual_usd="0.1", evidence="saved usage")
        self.assertEqual(Ledger.snapshot_status(self.path)["spent_usd"], "0.000000")
        self.ledger.export_snapshot()
        self.assertEqual(Ledger.snapshot_status(self.path), self.ledger.status())
        with sqlite3.connect(self.path.with_suffix(".sqlite3")) as connection:
            rows = [
                json.loads(r[0])
                for r in connection.execute("SELECT data FROM events ORDER BY sequence")
            ]
        self.assertEqual(
            [r["state"] for r in rows],
            ["reserved", "dispatching", "submitted", "settled"],
        )
        self.assertEqual(rows[2]["request_id"], "original")


if __name__ == "__main__":
    unittest.main()
