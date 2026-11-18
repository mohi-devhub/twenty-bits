"""Standing sampling replacements keep holds and never change the request."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

if importlib.util.find_spec("tinker") is None:
    raise unittest.SkipTest("Install .[paid] for mocked recovery checks.")

import tinker
from twenty_bits.budget import Ledger, BudgetError, CAP
from twenty_bits.recovery import RecoveringTransport, ReplacementApprovalRequired
from twenty_bits.tinker_transport import NetworkInterruption, save_json


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.root = root
        (root / "ledger.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "cap_usd": str(CAP),
                    "reservation_multiplier": "1.5",
                    "entries": [],
                    "blocks": [],
                }
            )
        )
        self.ledger = Ledger(root / "ledger.json")
        policy = {
            "authorized": True,
            "aggregate_unresolved_lost_original_holds_must_be_below_usd": "0.500000",
        }
        save_json(root / "policy.json", policy)
        save_json(root / "registry.json", {"legacy_lost_entry_ids": [], "cases": []})
        self.t = RecoveringTransport(
            {"run_id": "unit", "primary_model": "Qwen/Qwen3-8B", "ledger_phase": 4},
            root / "run",
            ledger=self.ledger,
            usage_path=root / "usage.jsonl",
            run_cap_usd="1",
            registry_path=root / "registry.json",
            policy_path=root / "policy.json",
        )

    def dispatched(self, key="original", amount=".01"):
        entry, _ = self.ledger.call(
            lambda: None,
            phase=4,
            operation="[unit] sample " + key,
            estimate_usd=amount,
            max_cost_usd=amount,
        )
        self.ledger.attach_request_id(entry, "unit:sample:0:1")
        path = self.t.directory / "requests" / f"{key}.json"
        journal = {
            "key": key,
            "entry_id": entry,
            "request_id": "unit:sample:0:1",
            "signature": "same",
            "request_id_saved_before_dispatch": True,
        }
        save_json(path, journal)
        return journal, path

    async def test_lost_original_stays_held_and_is_excluded(self):
        j, p = self.dispatched()
        before = self.ledger.status()["held_usd"]
        with self.assertRaises(NetworkInterruption):
            self.t.record_loss(j, p, "HTTP404")
        self.assertEqual(self.ledger.status()["held_usd"], before)
        self.assertFalse(json.loads(p.read_text())["output_allowed"])
        self.assertTrue(json.loads(p.read_text())["orphaned"])
        self.assertEqual(len(self.t.registry["cases"]), 1)

    async def test_second_loss_needs_approval_without_another_replacement(self):
        j, p = self.dispatched()
        with self.assertRaises(NetworkInterruption):
            self.t.record_loss(j, p, "HTTP404")
        case = self.t.registry["cases"][0]
        second, sp = self.dispatched(case["replacement_key"])
        with self.assertRaises(ReplacementApprovalRequired):
            self.t.record_loss(second, sp, "expired")
        self.assertTrue(case["requires_approval"])
        self.assertEqual(len(self.t.registry["cases"]), 1)

    async def test_half_dollar_limit_is_strict(self):
        j, p = self.dispatched(amount=".333333")
        # Reservation rounds 1.5x upward to exactly .500000.
        with self.assertRaises(ReplacementApprovalRequired):
            self.t.record_loss(j, p, "HTTP404")
        self.assertEqual(self.ledger.status()["held_usd"], "0.500000")

    async def test_changed_prompt_is_refused_before_dispatch(self):
        self.t.registry["cases"] = [
            {
                "logical_key": "turn",
                "original_entry_id": "unused",
                "replacement_key": "turn/approved-replacement-v1",
                "signature": "different",
            }
        ]
        with patch(
            "twenty_bits.rl_pilot.PilotTransport.sample", new_callable=AsyncMock
        ) as send:
            with self.assertRaises(BudgetError):
                await self.t.sample(
                    model="Qwen/Qwen3-8B",
                    key="turn",
                    prompt=tinker.ModelInput.from_ints([1]),
                    params=tinker.SamplingParams(max_tokens=2048, seed=4),
                )
            send.assert_not_called()
        self.assertEqual(self.ledger.status()["spent_usd"], "0.000000")

    async def test_missing_used_replacement_journal_cannot_create_another_attempt(self):
        self.t.registry["cases"] = [
            {
                "logical_key": "turn",
                "original_entry_id": "unused",
                "replacement_key": "turn/approved-replacement-v1",
                "signature": "same",
                "replacements_used": 1,
            }
        ]
        with self.assertRaises(ReplacementApprovalRequired):
            await self.t.sample(
                model="Qwen/Qwen3-8B",
                key="turn",
                prompt=tinker.ModelInput.from_ints([1]),
                params=tinker.SamplingParams(max_tokens=2048, seed=4),
            )
        self.assertEqual(len(self.ledger.status()["entries"]), 0)


if __name__ == "__main__":
    unittest.main()
