"""The follow-up changes only public budget text, including INVALID turns."""

import copy
import unittest

from twenty_bits.candidate_feedback import candidate_messages
from twenty_bits.game import Game
from twenty_bits.visible_budget import budget_text, visible_budget_messages
from twenty_bits.worlds import training_game


class VisibleBudgetTests(unittest.TestCase):
    def setUp(self):
        self.record = training_game(4, 600000, seed=20261120, noise=0)

    def test_exact_text_and_exhaustion_notice(self):
        self.assertEqual(budget_text(2, 4), "Questions left: 2 of 4")
        self.assertEqual(
            budget_text(0, 4),
            "Questions left: 0 of 4\nNo questions left. You must GUESS now.",
        )

    def test_every_user_turn_and_only_added_budget_text(self):
        game = Game(self.record, grammar_version="attribute-codes-v2")
        for _ in range(game.limit):
            game.step("ASK: unknown_attribute")
        before = copy.deepcopy(game.turns)
        original = candidate_messages(self.record, game.turns)
        amended = visible_budget_messages(self.record, game.turns)
        self.assertEqual(amended[0], original[0])
        for index, (a, b) in enumerate(zip(original, amended)):
            if a["role"] != "user":
                self.assertEqual(a, b)
            else:
                used = index // 2
                self.assertEqual(
                    b["content"], a["content"] + "\n" + budget_text(4 - used, 4)
                )
        self.assertEqual(before, game.turns)
        self.assertEqual(original, candidate_messages(self.record, game.turns))

    def test_target_is_never_used(self):
        changed = copy.deepcopy(self.record)
        changed["target"] = (changed["target"] + 1) % 4
        self.assertEqual(
            visible_budget_messages(self.record), visible_budget_messages(changed)
        )

    def test_noise_and_table_prefix_unchanged(self):
        noisy = {**self.record, "noise": 0.1}
        self.assertEqual(
            visible_budget_messages(noisy)[0], visible_budget_messages(self.record)[0]
        )
        self.assertEqual(
            visible_budget_messages(noisy)[1]["content"].splitlines()[0],
            candidate_messages(noisy)[1]["content"],
        )


if __name__ == "__main__":
    unittest.main()
