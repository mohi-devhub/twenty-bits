import json
import unittest
import numpy as np
from twenty_bits.evaluation import frozen_manifest, frozen_games
from twenty_bits.game import Game
from twenty_bits.worlds import ROOT, load_split


class ArtifactTests(unittest.TestCase):
    def test_frozen_bank_and_split_provenance(self):
        manifest = frozen_manifest()
        self.assertEqual(len(manifest["cells"]), 10)
        for cell in manifest["cells"]:
            games = frozen_games(cell["domain"], cell["n"], cell["noise"], 2)
            self.assertEqual(len(games), 2)
            if cell["domain"] == "animals":
                for record in games:
                    self.assertFalse(
                        set(record["world"]["names"]) & set(load_split()["train"])
                    )

    def test_saved_replays_match_exact_engine(self):
        for pair in json.loads((ROOT / "replays/games.json").read_text()):
            for player in pair["players"]:
                game = Game(pair["record"])
                for saved in player["trace"]["turns"]:
                    observed = game.step(saved["action"])
                    self.assertEqual(observed["answer"], saved["answer"])
                    np.testing.assert_allclose(
                        observed["posterior_after"], saved["posterior_after"]
                    )
                self.assertEqual(game.won, player["trace"]["won"])

    def test_paid_plans_include_margin_and_both_training_conditions(self):
        plans = json.loads((ROOT / "research/paid_plans.json").read_text())["plans"]
        for plan in plans:
            self.assertLessEqual(plan["forecast_with_margin_usd"], plan["cap_usd"])
            self.assertAlmostEqual(
                plan["forecast_with_margin_usd"], 1.5 * sum(plan["parts_usd"].values())
            )
            self.assertGreaterEqual(len(plan["seeds"]["A"]), 2)
            self.assertGreaterEqual(len(plan["seeds"]["B"]), 1)
            self.assertEqual(plan["cells"], 10)
            self.assertEqual(plan["kept_checkpoints_per_main_seed"], 1)


if __name__ == "__main__":
    unittest.main()
