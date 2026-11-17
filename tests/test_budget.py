"""Budget tests use temporary ledgers and fake calls. No credentials or network."""

from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from twenty_bits.budget import BudgetError, Ledger, money


def reserve_in_process(path: str) -> bool:
    try:
        Ledger(path).reserve(
            phase=2, operation="fake sample", estimate_usd="1", max_cost_usd="1"
        )
        return True
    except BudgetError:
        return False


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "ledger.json"
        self.path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "cap_usd": "30.000000",
                    "reservation_multiplier": "1.5",
                    "entries": [],
                    "blocks": [],
                }
            )
        )
        self.ledger = Ledger(self.path)

    def reserve(self, estimate="1", maximum="1"):
        return self.ledger.reserve(
            phase=2,
            operation="fake sample",
            estimate_usd=estimate,
            max_cost_usd=maximum,
        )

    def settle(self, entry_id, actual="1"):
        self.ledger.dispatch(entry_id, lambda: None)
        self.ledger.settle(entry_id, actual_usd=actual, evidence="fake-billing.json")

    def test_reserves_one_and_a_half_times_estimate(self):
        self.reserve("2", "2")
        self.assertEqual(self.ledger.status()["held_usd"], "3.000000")

    def test_full_maximum_wins_over_multiplier(self):
        self.reserve("1", "4")
        self.assertEqual(self.ledger.status()["held_usd"], "4.000000")

    def test_exact_cap_allowed_but_one_microdollar_more_refused(self):
        self.reserve("20", "20")
        before = self.path.read_bytes()
        with self.assertRaises(BudgetError):
            self.reserve("0.000001", "0.000001")
        self.assertEqual(self.path.read_bytes(), before)

    def test_rounds_up_without_binary_float_errors(self):
        self.reserve("0.000001", "0.000001")
        self.assertEqual(self.ledger.status()["held_usd"], "0.000002")
        self.assertEqual(money("0.1000001"), Decimal("0.100001"))

    def test_invalid_amounts_fail_closed(self):
        for bad in ["-1", "NaN", "Infinity", "bad", "1e99999", 0.1, None, True]:
            with self.subTest(bad=bad), self.assertRaises(BudgetError):
                money(bad)

    def test_maximum_cannot_be_below_estimate(self):
        with self.assertRaises(BudgetError):
            self.reserve("2", "1")

    def test_ledger_is_saved_before_callback_runs(self):
        def send():
            entry = Ledger(self.path).status()["entries"][0]
            self.assertEqual(entry["state"], "dispatching")
            self.assertEqual(entry["reserved_usd"], "1.500000")
            return "fake response"

        entry_id, result = self.ledger.call(
            send, phase=2, operation="fake sample", estimate_usd="1", max_cost_usd="1"
        )
        self.assertTrue(entry_id)
        self.assertEqual(result, "fake response")

    def test_over_budget_never_invokes_callback(self):
        self.reserve("20", "20")
        calls = []
        with self.assertRaises(BudgetError):
            self.ledger.call(
                lambda: calls.append(True),
                phase=2,
                operation="refused sample",
                estimate_usd="1",
                max_cost_usd="1",
            )
        self.assertEqual(calls, [])

    def test_failed_dispatch_keeps_hold_and_cannot_be_resubmitted(self):
        entry_id = self.reserve()

        def send():
            raise ConnectionError("The server may have accepted this request.")

        with self.assertRaises(ConnectionError):
            self.ledger.dispatch(entry_id, send)
        self.assertEqual(Ledger(self.path).status()["held_usd"], "1.500000")
        with self.assertRaises(BudgetError):
            self.ledger.dispatch(entry_id, lambda: self.fail("Duplicate submission"))
        with self.assertRaises(BudgetError):
            self.ledger.void(entry_id, reason="timeout does not mean free")

    def test_408_keeps_the_same_request_id_and_hold(self):
        entry_id = self.reserve()
        submissions = []
        self.ledger.dispatch(entry_id, lambda: submissions.append("request-123"))
        self.ledger.attach_request_id(entry_id, "request-123")
        for _ in range(3):
            # A pending result is not a settlement or a new submission.
            self.ledger.attach_request_id(entry_id, "request-123")
        self.assertEqual(submissions, ["request-123"])
        self.assertEqual(self.ledger.status()["held_usd"], "1.500000")
        with self.assertRaises(BudgetError):
            self.ledger.attach_request_id(entry_id, "replacement-id")

    def test_settlement_releases_hold_and_records_actual(self):
        entry_id = self.reserve("2", "3")
        self.settle(entry_id, "2.25")
        status = self.ledger.status()
        self.assertEqual(status["spent_usd"], "2.250000")
        self.assertEqual(status["held_usd"], "0.000000")
        self.assertEqual(status["available_usd"], "27.750000")
        self.assertEqual(status["entries"][0]["evidence"], "fake-billing.json")

    def test_pending_and_settled_money_both_count(self):
        entry_id = self.reserve("10", "10")
        self.settle(entry_id, "10")
        self.reserve("10", "10")
        with self.assertRaises(BudgetError):
            self.reserve("4", "4")

    def test_settlement_is_idempotent_and_cannot_lower_recorded_cost(self):
        entry_id = self.reserve()
        self.settle(entry_id)
        self.ledger.settle(entry_id, actual_usd="1", evidence="fake-billing.json")
        self.assertEqual(self.ledger.status()["spent_usd"], "1.000000")
        with self.assertRaises(BudgetError):
            self.ledger.settle(entry_id, actual_usd="0.5", evidence="different.json")

    def test_unknown_cost_cannot_be_recorded_as_zero_without_evidence(self):
        entry_id = self.reserve()
        self.ledger.dispatch(entry_id, lambda: None)
        with self.assertRaises(BudgetError):
            self.ledger.settle(entry_id, actual_usd="0", evidence="")
        self.assertEqual(self.ledger.status()["held_usd"], "1.500000")

    def test_breach_records_truth_then_blocks_more_calls(self):
        entry_id = self.reserve("1", "1")
        self.settle(entry_id, "1.2")
        self.assertEqual(self.ledger.status()["spent_usd"], "1.200000")
        self.assertTrue(self.ledger.status()["blocked"])
        with self.assertRaises(BudgetError):
            self.reserve("0", "0")

    def test_existing_reservation_cannot_dispatch_after_breach(self):
        first = self.reserve()
        waiting = self.reserve()
        self.settle(first, "2")
        with self.assertRaises(BudgetError):
            self.ledger.dispatch(waiting, lambda: self.fail("Dispatch after breach"))

    def test_void_only_releases_unsubmitted_work(self):
        entry_id = self.reserve()
        self.ledger.void(entry_id, reason="The offline preflight rejected the run.")
        self.assertEqual(self.ledger.status()["available_usd"], "30.000000")
        with self.assertRaises(BudgetError):
            self.ledger.dispatch(entry_id, lambda: self.fail("Voided work"))

    def test_free_metadata_call_is_recorded(self):
        entry_id, _ = self.ledger.call(
            lambda: None,
            phase=0,
            operation="fake capabilities",
            estimate_usd="0",
            max_cost_usd="0",
        )
        self.ledger.settle(entry_id, actual_usd="0", evidence="fake metadata response")
        self.assertEqual(len(self.ledger.status()["entries"]), 1)
        self.assertEqual(self.ledger.status()["spent_usd"], "0.000000")

    def test_missing_corrupt_or_weakened_ledger_never_calls_provider(self):
        for content in [
            None,
            "{",
            '{"schema_version": 0}',
            self.path.read_text().replace("30.000000", "300.000000"),
        ]:
            with self.subTest(content=content):
                if content is None:
                    self.path.unlink()
                else:
                    self.path.write_text(content)
                with self.assertRaises(BudgetError):
                    self.ledger.call(
                        lambda: self.fail("Bad ledger reached provider"),
                        phase=2,
                        operation="sample",
                        estimate_usd="1",
                        max_cost_usd="1",
                    )

    def test_tampered_reservation_is_rejected(self):
        self.reserve()
        data = json.loads(self.path.read_text())
        data["entries"][0]["reserved_usd"] = "0.000000"
        self.path.write_text(json.dumps(data))
        with self.assertRaises(BudgetError):
            self.ledger.status()

    def test_whole_run_preflight_refuses_unaffordable_schedule(self):
        with self.assertRaises(BudgetError):
            self.ledger.check_run(estimate_usd="21", max_cost_usd="21")
        self.assertEqual(self.ledger.status()["entries"], [])

    def test_parallel_processes_cannot_overbook(self):
        with ProcessPoolExecutor(max_workers=4) as pool:
            outcomes = list(pool.map(reserve_in_process, [str(self.path)] * 28))
        self.assertEqual(sum(outcomes), 20)
        self.assertEqual(self.ledger.status()["held_usd"], "30.000000")
        self.assertEqual(len(self.ledger.status()["entries"]), 20)


if __name__ == "__main__":
    unittest.main()
