"""Exact header aliases and lexical collisions, without service calls."""

import unittest
import numpy as np
from twenty_bits.attributes import attribute_aliases, attribute_code
from twenty_bits.game import Game
from twenty_bits.predicates import ParseError, parse
from twenty_bits.prompts import prefix
from twenty_bits.worlds import World, load_world


class AttributeAliasTests(unittest.TestCase):
    def setUp(self):
        self.world = World(
            "unit",
            ("fur", "aquatic"),
            ("a", "item", "not", "AND"),
            np.array([[1, 0], [1, 1], [0, 1], [0, 0]], dtype=np.uint8),
        )
        self.aliases = attribute_aliases(self.world.attributes)

    def mask(self, text, aliases=None):
        aliases = self.aliases if aliases is None else aliases
        return (
            parse(text, aliases=aliases)
            .evaluate(
                self.world.attributes,
                self.world.names,
                self.world.rows,
                aliases=aliases,
            )
            .tolist()
        )

    def test_header_and_parser_share_codes(self):
        self.assertIn("a=fur,b=aquatic", prefix(self.world))
        self.assertEqual(self.mask("a AND NOT aquatic"), [True, False, False, False])
        self.assertEqual(self.mask("fur AND NOT b"), self.mask("a AND NOT aquatic"))
        self.assertEqual(attribute_code(25), "z")
        self.assertEqual(attribute_code(26), "aa")
        self.assertEqual(attribute_code(171846), "item")

    def test_aliases_are_exact_and_case_sensitive(self):
        for text in ("A", "aa", "Fur", "aquati", "b0", "a_", "a.a"):
            with self.subTest(text=text), self.assertRaises(ParseError):
                self.mask(text)
        self.assertEqual(self.mask("NOT a"), [False, False, True, True])

    def test_codes_follow_the_current_subset_after_constant_columns_drop(self):
        subset = self.world.subset([0, 1])
        self.assertEqual(subset.attributes, ("aquatic",))
        self.assertIn("a=aquatic", prefix(subset))
        aliases = attribute_aliases(subset.attributes)
        mask = parse("a", aliases=aliases).evaluate(
            subset.attributes, subset.names, subset.rows, aliases=aliases
        )
        self.assertEqual(mask.tolist(), [False, True])

    def test_codes_and_item_names_have_separate_contexts(self):
        self.assertEqual(self.mask("a"), [True, True, False, False])
        self.assertEqual(self.mask("item == a"), [True, False, False, False])
        self.assertEqual(self.mask('b AND item == "not"'), [False, False, True, False])
        self.assertEqual(
            self.mask('NOT a AND item == "AND"'), [False, False, False, True]
        )
        with self.assertRaises(ParseError):
            self.mask("item == AND")

    def test_keyword_like_codes(self):
        # These lowercase codes occur in sufficiently wide base-26 headers.
        aliases = {"item": "fur", "not": "aquatic", "and": "fur", "or": "aquatic"}
        self.assertEqual(
            self.mask("item AND NOT not", aliases), [True, False, False, False]
        )
        self.assertEqual(self.mask("and OR or", aliases), [True, True, True, False])
        self.assertEqual(
            self.mask("item == item OR not", aliases), [False, True, True, False]
        )
        with self.assertRaises(ParseError):
            self.mask("NOT", aliases)

    def test_ambiguous_code_and_full_name_headers_are_rejected(self):
        with self.assertRaises(ValueError):
            attribute_aliases(("b", "fur"))
        self.assertEqual(attribute_aliases(("a", "b")), {"a": "a", "b": "b"})

    def test_real_world_headers_have_no_alias_collisions(self):
        for domain in ("animals", "tools", "foods", "synthetic"):
            self.assertEqual(
                len(attribute_aliases(load_world(domain).attributes)),
                len(load_world(domain).attributes),
            )

    def test_game_alias_matches_full_name_math_and_reward(self):
        record = {
            "id": "alias-unit",
            "domain": "unit",
            "n": 4,
            "target": 0,
            "noise": 0.1,
            "noise_seed": 3,
            "world": self.world.to_dict(),
        }
        code_game, name_game = Game(record), Game(record)
        code = code_game.step("ASK: a AND NOT b")
        name = name_game.step("ASK: fur AND NOT aquatic")
        for field in ("answer", "eig", "posterior_after", "flipped", "invalid"):
            self.assertEqual(code[field], name[field])
        self.assertEqual(code_game.reward, name_game.reward)
        self.assertTrue(
            Game(record, grammar_version="names-v1").step("ASK: a")["invalid"]
        )


if __name__ == "__main__":
    unittest.main()
