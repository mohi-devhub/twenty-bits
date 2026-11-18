"""Training-pool probe boundaries and the additional run spending limit."""

import json
import importlib.util
from pathlib import Path
import tempfile
import unittest

from twenty_bits.budget import CAP, BudgetError, Ledger, money
from twenty_bits.learnability import probe_messages, probe_records, prompt_examples
from twenty_bits.predicates import parse
from twenty_bits.prompts import messages
from twenty_bits.worlds import ROOT, World, load_split, training_game


class ProbePromptTests(unittest.TestCase):
    def test_examples_are_valid_and_public_prompt_hides_target(self):
        for record in probe_records():
            world = World.from_dict(record["world"])
            for example in prompt_examples(world):
                expression = parse(example[5:])
                self.assertEqual(expression.named_items, 0)
                expression.evaluate(world.attributes, world.names, world.rows)
            other = {**record, "target": (record["target"] + 1) % record["n"]}
            self.assertEqual(probe_messages(record), probe_messages(other))
            self.assertIn("GRAMMAR EXAMPLES", probe_messages(record)[0]["content"])
            self.assertNotIn("GRAMMAR EXAMPLES", messages(record)[0]["content"])
            self.assertTrue(set(world.names) <= set(load_split()["train"]))
            self.assertFalse(set(world.names) & set(load_split()["held_out"]))

    def test_smaller_sizes_preserve_training_boundary(self):
        for n in (4, 8):
            self.assertEqual(training_game(n, 99, seed=11, noise=0)["n"], n)
        for n in (2, 12, 256):
            with self.assertRaises(ValueError):
                training_game(n, 99, seed=11, noise=0)


@unittest.skipUnless(
    importlib.util.find_spec("tinker"), "Install .[paid] for adapter-budget tests."
)
class ProbeBudgetTests(unittest.TestCase):
    def test_subcap_counts_pending_holds_and_survives_a_new_transport(self):
        from twenty_bits.tinker_transport import GuardedTinker

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "ledger.json"
            path.write_text(
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
            ledger = Ledger(path)
            config = json.loads((ROOT / "evals/phase2.json").read_text())
            config["run_id"] = "test-probe"
            transport = GuardedTinker(
                config,
                root / "run",
                ledger=ledger,
                usage_path=root / "usage.jsonl",
                run_cap_usd="1.50",
            )
            entry, _ = transport.call(
                lambda: None,
                operation="sample pending",
                estimate_usd="1",
                max_cost_usd="1",
            )
            self.assertEqual(money(transport.run_status()["held_usd"]), money("1.50"))
            resumed = GuardedTinker(
                config,
                root / "run",
                ledger=ledger,
                usage_path=root / "usage.jsonl",
                run_cap_usd="1.50",
            )
            dispatched = []
            with self.assertRaises(BudgetError):
                resumed.call(
                    lambda: dispatched.append(True),
                    operation="another sample",
                    estimate_usd="0.01",
                    max_cost_usd="0.01",
                )
            self.assertFalse(dispatched)
            ledger.settle(entry, actual_usd="0.9", evidence="mock observed cost")
            resumed.call(
                lambda: None,
                operation="fits exactly",
                estimate_usd="0.4",
                max_cost_usd="0.4",
            )
            status = resumed.run_status()
            self.assertEqual(
                money(status["spent_usd"]) + money(status["held_usd"]), money("1.50")
            )


if __name__ == "__main__":
    unittest.main()
