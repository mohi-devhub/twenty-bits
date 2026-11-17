from decimal import Decimal
import json
from pathlib import Path
import unittest

from twenty_bits.costs import game_tokens, grid_cost, projection, sample_cost


class CostTests(unittest.TestCase):
    def test_hand_counted_n16_prompt_and_history(self):
        # Five prompts of 896 tokens. Prior turns contribute 0+1+2+3+4
        # history blocks of 160 tokens. Five outputs each use 128 tokens.
        self.assertEqual(game_tokens(16, stress=False), (6080, 640))

    def test_input_and_output_prices_have_per_million_units(self):
        rates = {
            "prefill": Decimal("2"),
            "cached_prefill": Decimal("0.4"),
            "sample": Decimal("3"),
        }
        self.assertEqual(
            sample_cost((1_000_000, 2_000_000), rates, cached=False), Decimal("8")
        )
        self.assertEqual(
            sample_cost((1_000_000, 2_000_000), rates, cached=True), Decimal("6.4")
        )

    def test_grid_has_8000_games(self):
        # At a fictitious flat $1 per generated token and free input, the
        # grid costs exactly its generated token count: 7,168,000.
        rates = {
            "prefill": Decimal(0),
            "cached_prefill": Decimal(0),
            "sample": Decimal(1_000_000),
        }
        self.assertEqual(
            grid_cost(200, rates, stress=False, cached=False), Decimal(7_168_000)
        )

    def test_six_full_evals_exceed_cap_even_in_cached_scenario(self):
        catalog = json.loads(
            (
                Path(__file__).resolve().parent.parent
                / "research/tinker-models-2026-11-17.json"
            ).read_text()
        )
        result = projection(catalog)
        cheap = result["scenarios"]["optimistic_all_prefill_cached"]["phases"]["4"]
        self.assertGreater(cheap["six_final_full_evals_48000_games"], Decimal(30))


if __name__ == "__main__":
    unittest.main()
