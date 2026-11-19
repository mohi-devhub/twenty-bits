"""Separate guessing with budget left from forced guesses and extra asks."""

import unittest
from twenty_bits.budget_followup_metrics import flags, summarize


class BudgetFollowupMetricTests(unittest.TestCase):
    def game(self, *, k=None, q=10, won=False, ask=False):
        return {
            "n": 32,
            "guess_state": None if k is None else {"k_remaining": k},
            "questions": q,
            "won": won,
            "early_guess": k is not None and q < 5,
            "question_eigs": [0.5] * q,
            "invalid_count": 0,
            "truncation_count": 0,
            "enumeration_count": 0,
            "turns": [
                {
                    "question_index": q,
                    "is_question": False,
                    "action": "ASK: a" if ask else "GUESS: x",
                }
            ],
        }

    def test_only_ambiguous_guesses_before_exhaustion_count(self):
        self.assertTrue(flags(self.game(k=3, q=4))["ambiguous_with_budget_left"])
        self.assertFalse(flags(self.game(k=3, q=10))["ambiguous_with_budget_left"])
        self.assertFalse(flags(self.game(k=1, q=4))["ambiguous_with_budget_left"])
        self.assertFalse(flags(self.game(q=10, ask=True))["ambiguous_with_budget_left"])

    def test_counts_retain_no_guess_games_and_do_not_reward_extra_asks(self):
        games = [
            self.game(k=3, q=4, won=True),
            self.game(k=2),
            self.game(ask=True),
            self.game(k=1, q=3, won=True),
        ]
        result = summarize(games)
        self.assertEqual(result["wins"], 2)
        self.assertEqual(result["ambiguous_with_budget_left_games"], 1)
        self.assertEqual(result["no_guess_games"], 1)
        self.assertEqual(result["extra_ask_final_games"], 1)
        self.assertEqual(result["early_guess_win_games"], 2)
        self.assertEqual(result["no_guess_rate"], 0.25)
        self.assertEqual(result["eig_per_question"], 0.5)


if __name__ == "__main__":
    unittest.main()
