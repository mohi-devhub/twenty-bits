"""Hand checks for stopping rates and the single-B, two-A uncertainty model."""

import unittest
import numpy as np
from scripts.analyze_all_main_seeds import b_vs_a, finite_interval, statistics


def game(index, eig=0.2, *, noise=0, domain="animals"):
    return {
        "domain": domain,
        "n": 32,
        "noise": noise,
        "game_id": f"{domain}/{index}/{noise}",
        "won": index % 2 == 0,
        "questions": 1,
        "question_eigs": [eig],
        "early_guess": False,
        "guess_state": {"k_remaining": 1},
        "reasks_after_low_probability": 0,
        "low_probability_opportunities": 0,
    }


class MainComparisonTests(unittest.TestCase):
    def test_question_weighting_and_all_game_stopping_denominators(self):
        a = game(0, 1)
        a["early_guess"] = True
        b = game(1, 0.5)
        b.update(
            questions=3, question_eigs=[0.5, 0.5, 0.5], guess_state={"k_remaining": 3}
        )
        r = statistics([a, b], np.arange(2))
        self.assertAlmostEqual(float(r["eig_per_question"]), 0.625)
        self.assertEqual(float(r["win_rate"]), 0.5)
        self.assertEqual(float(r["questions_per_win"]), 1)
        self.assertEqual(float(r["ambiguous_guess_rate"]), 0.5)
        self.assertEqual(float(r["early_guess_win_rate"]), 0.5)
        b["guess_state"] = None
        self.assertEqual(float(statistics([a, b], np.arange(2))["no_guess_rate"]), 0.5)

    def test_no_recheck_opportunities_is_undefined(self):
        r = statistics([game(0)], np.arange(1))
        self.assertTrue(np.isnan(r["recheck_rate"]))
        self.assertEqual(
            finite_interval([np.nan, np.nan]), {"ci95": None, "defined_draws": 0}
        )

    def cohorts(self):
        cells = [(d, 32, p) for d in ["animals", "synthetic"] for p in [0, 0.1]]
        games = [game(i, noise=p, domain=d) for d, n, p in cells for i in range(28)]
        return cells, {name: [dict(g) for g in games] for name in ["A11", "A23", "B41"]}

    def test_identical_endpoints_have_zero_condition_difference(self):
        cells, cohorts = self.cohorts()
        r = b_vs_a(cohorts, cells, draws=200)
        self.assertEqual(r["B_seeds"], [41])
        for subset in r["subsets"].values():
            self.assertAlmostEqual(subset["eig_per_question"]["B41_minus_mean_A"], 0)
            np.testing.assert_allclose(subset["eig_per_question"]["ci95"], [0, 0])

    def test_two_A_seeds_contribute_uncertainty_with_one_fixed_B(self):
        cells, cohorts = self.cohorts()
        for g in cohorts["A11"]:
            g["question_eigs"] = [0.1]
        for g in cohorts["A23"]:
            g["question_eigs"] = [0.3]
        r = b_vs_a(cohorts, cells, draws=400)["subsets"]["noisy_animals"][
            "eig_per_question"
        ]
        self.assertAlmostEqual(r["B41_minus_mean_A"], 0)
        np.testing.assert_allclose(r["ci95"], [-0.1, 0.1])


if __name__ == "__main__":
    unittest.main()
