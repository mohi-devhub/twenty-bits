"""Hand cases for paired endpoint statistics; no service access."""

import unittest
from scripts.analyze_main_evaluation import paired_cell


def game(i, won, eig, q=2):
    return {
        "game_id": str(i),
        "won": won,
        "questions": q,
        "question_eigs": [eig] * q,
        "eig_per_question": eig,
    }


class MainStatisticsTests(unittest.TestCase):
    def test_identical_pairs_have_zero_change_and_unit_win_p(self):
        games = [game(0, True, 1), game(1, False, 0.5)]
        result, _ = paired_cell(games, games)
        self.assertEqual(result["win_rate"]["ci95"], [0, 0])
        self.assertEqual(result["eig_per_question"]["ci95"], [0, 0])
        self.assertEqual(result["exact_paired_win_p"], 1)

    def test_three_discordant_wins_give_exact_two_sided_quarter(self):
        base = [game(i, False, 0.5) for i in range(8)]
        final = [game(i, i < 3, 0.75) for i in range(8)]
        result, _ = paired_cell(base, final)
        self.assertEqual(result["exact_paired_win_p"], 0.25)
        self.assertAlmostEqual(result["win_rate"]["final_minus_base"], 3 / 8)
        self.assertAlmostEqual(result["eig_per_question"]["final_minus_base"], 0.25)

    def test_eig_uses_question_weighting_and_undefined_wins_stay_undefined(self):
        base = [game(0, False, 1, 1), game(1, False, 0, 3)]
        final = [game(0, False, 1, 1), game(1, False, 1, 3)]
        result, _ = paired_cell(base, final)
        self.assertEqual(result["eig_per_question"]["final_minus_base"], 0.75)
        self.assertIsNone(result["questions_per_win"]["final_minus_base"])
        self.assertIsNone(result["questions_per_win"]["ci95"])


if __name__ == "__main__":
    unittest.main()
