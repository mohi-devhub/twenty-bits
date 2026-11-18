import unittest

import numpy as np

from twenty_bits.game import Game
from twenty_bits.suffix_diagnostic import SuffixDiagnosticGame, suffix_aliases
from twenty_bits.worlds import World


def record(attributes=("a_123", "a_456"), names=("b_123", "other")):
    world = World(
        "synthetic",
        attributes,
        names,
        np.array(
            [[1] + [0] * (len(attributes) - 1), [0] * len(attributes)], dtype=np.uint8
        ),
    )
    return {
        "id": "unit/suffix",
        "domain": "synthetic",
        "n": 2,
        "world": world.to_dict(),
        "target": 0,
        "noise": 0,
        "noise_seed": 17,
    }


class SuffixDiagnosticTests(unittest.TestCase):
    def test_mapping_changes_only_the_diagnostic_answer_and_preserves_raw_text(self):
        r = record()
        primary = Game(r)
        diagnostic = SuffixDiagnosticGame(r)
        self.assertEqual(primary.step("ASK: b_123")["answer"], "INVALID")
        turn = diagnostic.step("ASK: b_123")
        self.assertEqual(turn["answer"], "YES")
        self.assertEqual(turn["raw_action"], "ASK: b_123")
        self.assertEqual(turn["suffix_mapped_identifiers"], 1)
        self.assertAlmostEqual(turn["eig"], 1)
        self.assertEqual(Game(r).step("ASK: b_123")["answer"], "INVALID")

    def test_real_names_and_exact_codes_keep_primary_meaning(self):
        for action in ("ASK: a_123", "ASK: a"):
            primary, diagnostic = Game(record()), SuffixDiagnosticGame(record())
            a, b = primary.step(action), diagnostic.step(action)
            self.assertEqual(a["answer"], b["answer"])
            self.assertEqual(b["suffix_mapped_identifiers"], 0)

    def test_ambiguous_suffix_is_not_mapped_and_real_names_take_priority(self):
        self.assertNotIn("c_123", suffix_aliases(("a_123", "z_123", "a_456")))
        g = SuffixDiagnosticGame(record(("a_123", "b_123")))
        self.assertEqual(g.step("ASK: b_123")["answer"], "NO")
        self.assertEqual(g.turns[-1]["suffix_mapped_identifiers"], 0)

    def test_unknown_codes_case_changes_and_missing_suffixes_stay_invalid(self):
        for action in ("ASK: z_123", "ASK: B_123", "ASK: b_999", "ASK: b_"):
            turn = SuffixDiagnosticGame(record()).step(action)
            self.assertTrue(turn["invalid"])
            self.assertEqual(turn["suffix_mapped_identifiers"], 0)

    def test_item_names_and_guesses_are_literal(self):
        for action, answer in (("ASK: item == b_123", "YES"), ("GUESS: b_123", "WIN")):
            turn = SuffixDiagnosticGame(record()).step(action)
            self.assertEqual(turn["answer"], answer)
            self.assertEqual(turn["suffix_mapped_identifiers"], 0)

    def test_mixed_predicate_counts_each_resolved_identifier(self):
        turn = SuffixDiagnosticGame(record()).step("ASK: b_123 AND NOT b AND b_123")
        self.assertEqual(turn["answer"], "YES")
        self.assertEqual(turn["suffix_mapped_identifiers"], 2)

    def test_malformed_and_malicious_input_keep_primary_limits(self):
        for action in (
            "ASK: b_123; print(1)",
            "ASK: b_123 AND",
            "ASK: " + "NOT " * 70 + "b_123",
        ):
            self.assertTrue(SuffixDiagnosticGame(record()).step(action)["invalid"])

    def test_semantic_domain_is_rejected(self):
        r = record()
        r["domain"] = "animals"
        with self.assertRaises(ValueError):
            SuffixDiagnosticGame(r)
