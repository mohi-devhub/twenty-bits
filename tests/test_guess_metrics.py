"""Stopping counts use the exact public state immediately before a guess."""

import unittest
from twenty_bits.guess_metrics import guess_state, guess_summary


class GuessMetricsTests(unittest.TestCase):
    def game(self, posterior, *, won=False, guess="a", noise=0):
        record = {"noise": noise, "world": {"names": ["a", "b", "c", "d"]}}
        game = {
            "turns": [
                {
                    "action": "GUESS: " + guess,
                    "posterior_before": posterior,
                    "answer": "WIN" if won else "LOSS",
                }
            ]
        }
        game["guess_state"] = guess_state(game, record)
        return game

    def test_noiseless_support_is_measured_before_the_guess(self):
        for k in (1, 2, 3, 4):
            state = self.game([1 / k] * k + [0] * (4 - k))["guess_state"]
            self.assertEqual(state["k_remaining"], k)
            self.assertEqual(state["bin"], str(k) if k < 4 else "4+")

    def test_noisy_list_is_thresholded_but_full_support_is_retained(self):
        state = self.game([0.998, 0.001, 0.0005, 0.0005], noise=0.1)["guess_state"]
        self.assertEqual(state["k_remaining"], 1)
        self.assertEqual(state["positive_posterior_support"], 4)
        self.assertEqual(state["definition"], "displayed_threshold_plus_top")

    def test_counts_and_wins_keep_no_guess_games_in_the_denominator(self):
        games = [
            self.game([0.5, 0.5, 0, 0], won=True),
            self.game([0.5, 0.5, 0, 0]),
            self.game([1 / 3] * 3 + [0], won=True),
            self.game([0.25] * 4),
            {"guess_state": None},
        ]
        result = guess_summary(games)
        self.assertEqual(result["no_guess_games"], 1)
        self.assertEqual(result["bins"]["2"]["guesses"], 2)
        self.assertEqual(result["bins"]["2"]["wins"], 1)
        self.assertEqual(result["bins"]["2"]["guesses_per_game"], 0.4)
        self.assertEqual(result["bins"]["2"]["share_of_guesses"], 0.5)
        self.assertEqual(result["bins"]["2"]["win_rate_when_guessed"], 0.5)

    def test_eliminated_and_unknown_guesses_still_count(self):
        for guess in ("b", "outside"):
            state = self.game([1, 0, 0, 0], guess=guess)["guess_state"]
            self.assertFalse(state["guessed_in_displayed_candidates"])
            self.assertEqual(state["guessed_posterior_probability"], 0)
            self.assertEqual(state["bin"], "1")

    def test_a_budget_ending_without_a_guess_has_no_guess_state(self):
        game = {"turns": [{"action": "ASK: a", "answer": "LOSS"}]}
        self.assertIsNone(guess_state(game, {}))


if __name__ == "__main__":
    unittest.main()
