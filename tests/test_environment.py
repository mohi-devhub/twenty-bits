import unittest
import numpy as np
from twenty_bits.predicates import ParseError, parse
from twenty_bits.information import entropy, expected_gain, update
from twenty_bits.worlds import World, load_split, load_world, sample_game, training_game
from twenty_bits.game import Game
from twenty_bits.prompts import messages


def example(noise=0):
    world = World(
        "test",
        ("fur", "water"),
        ("cat", "seal", "fish", "bird"),
        np.array([[1, 0], [1, 1], [0, 1], [0, 0]], dtype=np.uint8),
    )
    return {
        "id": "unit/0",
        "domain": "test",
        "n": 4,
        "world": world.to_dict(),
        "target": 0,
        "noise": noise,
        "noise_seed": 17,
    }


class ParserTests(unittest.TestCase):
    def evaluate(self, text):
        w = World.from_dict(example()["world"])
        return parse(text).evaluate(w.attributes, w.names, w.rows).tolist()

    def test_precedence_and_parentheses(self):
        self.assertEqual(
            self.evaluate("fur OR water AND NOT fur"), [True, True, True, False]
        )
        self.assertEqual(
            self.evaluate("(fur OR water) AND NOT fur"), [False, False, True, False]
        )

    def test_negation_and_equality(self):
        self.assertEqual(self.evaluate("NOT NOT fur"), [True, True, False, False])
        self.assertEqual(
            self.evaluate('item == cat OR item == "fish"'), [True, False, True, False]
        )
        self.assertEqual(parse('item == "red fox"').value, "red fox")

    def test_bad_and_malicious_input(self):
        invalid = [
            "",
            "fur water",
            "fur AND",
            "AND fur",
            "fur and water",
            "fur == water",
            "fur; print(1)",
            '__import__("os").system("echo bad")',
            "().__class__",
            "fur[0]",
            "fur | water",
            "1",
            "True",
            "item != cat",
            "item ==",
            "item == AND",
            "(fur",
            "fur)",
            "fur\x00",
            "NOT " * 70 + "fur",
            "(" * 70 + "fur" + ")" * 70,
            "x" * 40000,
        ]
        for expression in invalid:
            with self.subTest(expression=expression), self.assertRaises(ParseError):
                self.evaluate(expression)

    def test_long_flat_predicates_do_not_exhaust_python_recursion(self):
        self.assertEqual(
            self.evaluate(" AND ".join(["fur"] * 1000)), [True, True, False, False]
        )

    def test_unknown_symbols_are_invalid(self):
        for expression in ["missing", "item == absent"]:
            with self.assertRaises(ParseError):
                self.evaluate(expression)

    def test_enumeration_is_legal(self):
        e = parse("item == cat OR item == seal")
        self.assertEqual(e.named_items, 2)
        self.assertEqual(
            self.evaluate("item == cat OR item == seal"), [True, True, False, False]
        )


class InformationTests(unittest.TestCase):
    def test_entropy_hand_cases(self):
        self.assertAlmostEqual(entropy(np.ones(4) / 4), 2)
        self.assertAlmostEqual(entropy(np.array([1, 0, 0, 0])), 0)
        self.assertAlmostEqual(entropy(np.array([0.5, 0.25, 0.25])), 1.5)

    def test_noiseless_update(self):
        p = update(np.ones(4) / 4, np.array([True, True, False, False]), True, 0)
        np.testing.assert_allclose(p, [0.5, 0.5, 0, 0])

    def test_noisy_update_hand_cases(self):
        p = update(np.ones(2) / 2, np.array([True, False]), True, 0.1)
        np.testing.assert_allclose(p, [0.9, 0.1])
        q = update(p, np.array([True, False]), False, 0.1)
        np.testing.assert_allclose(q, [0.5, 0.5])

    def test_eig_ceilings_and_useless_questions(self):
        p = np.ones(4) / 4
        mask = np.array([True, True, False, False])
        self.assertAlmostEqual(float(expected_gain(p, mask, 0)), 1)
        self.assertAlmostEqual(float(expected_gain(p, mask, 0.1)), 0.5310044064107188)
        self.assertAlmostEqual(float(expected_gain(p, np.ones(4, dtype=bool), 0.1)), 0)

    def test_expected_entropy_change_equals_eig(self):
        p = np.array([0.6, 0.2, 0.1, 0.1])
        mask = np.array([True, False, False, False])
        noise = 0.1
        yes = noise + (1 - 2 * noise) * float(mask @ p)
        realized = sum(
            prob * (entropy(p) - entropy(update(p, mask, answer, noise)))
            for answer, prob in [(True, yes), (False, 1 - yes)]
        )
        self.assertAlmostEqual(realized, float(expected_gain(p, mask, noise)))

    def test_surprise_can_increase_entropy(self):
        p = np.array([0.9, 0.1])
        q = update(p, np.array([True, False]), False, 0.1)
        self.assertLess(entropy(p) - entropy(q), 0)


class GameTests(unittest.TestCase):
    def test_exact_answerer_and_win(self):
        g = Game(example())
        t = g.step("ASK: fur")
        self.assertEqual(t["answer"], "YES")
        self.assertEqual(t["eig"], 1)
        np.testing.assert_allclose(g.posterior, [0.5, 0.5, 0, 0])
        g.step("ASK: water")
        g.step("GUESS: cat")
        self.assertTrue(g.won)
        self.assertAlmostEqual(g.reward, 0.94)

    def test_outer_whitespace_is_allowed_but_extra_actions_are_invalid(self):
        g = Game(example())
        turn = g.step("  ASK: fur\n")
        self.assertEqual(turn["answer"], "YES")
        self.assertEqual(turn["raw_action"], "  ASK: fur\n")
        self.assertEqual(g.step("ASK: fur\nGUESS: cat")["answer"], "INVALID")
        self.assertEqual(parse("item == cat OR item == cat").named_items, 1)

    def test_wrong_guess_ends_game(self):
        g = Game(example())
        g.step("GUESS: fish")
        self.assertTrue(g.done)
        self.assertFalse(g.won)
        with self.assertRaises(ValueError):
            g.step("GUESS: cat")

    def test_invalid_costs_question_and_zero_information(self):
        g = Game(example())
        t = g.step('ASK: __import__("os")')
        self.assertEqual(t["answer"], "INVALID")
        self.assertEqual(g.questions, 1)
        self.assertEqual(t["eig"], 0)
        self.assertAlmostEqual(g.reward, -0.13)
        np.testing.assert_allclose(g.posterior, [0.25] * 4)

    def test_noise_schedule_is_seeded_and_policy_independent(self):
        a, b = Game(example(0.1)), Game(example(0.1))
        self.assertEqual(a.flips, b.flips)
        for x, y in [("fur", "water"), ("water", "fur")]:
            ta = a.step("ASK: " + x)
            tb = b.step("ASK: " + y)
            self.assertEqual(ta["flipped"], tb["flipped"])
        changed = example(0.1)
        changed["noise_seed"] = 31
        self.assertNotEqual(Game(changed).flips, Game(example(0.1)).flips)

    def test_reask_uses_semantics_and_handles_complements(self):
        g = Game(example(0.1))
        g.step("ASK: fur")
        t = g.step("ASK: NOT fur")
        self.assertTrue(t["reask"])

    def test_enumeration_is_logged(self):
        g = Game(example())
        t = g.step("ASK: item == cat OR item == fish")
        self.assertTrue(t["enumeration"])
        self.assertEqual(t["named_items"], 2)

    def test_last_answer_allows_a_final_guess(self):
        g = Game(example())
        for _ in range(g.limit):
            g.step("ASK: fur")
        g.step("GUESS: cat")
        self.assertTrue(g.won)

    def test_question_budget_cannot_be_exceeded(self):
        g = Game(example())
        for _ in range(g.limit):
            g.step("ASK: fur")
        g.step("ASK: water")
        self.assertTrue(g.done)
        self.assertFalse(g.won)
        self.assertEqual(g.questions, g.limit)

    def test_guesses_after_surprise_remain_in_recheck_denominator(self):
        record = example(0.1)
        record["noise_seed"] = 31
        g = Game(record)
        g.posterior = np.array([0.9, 0.1, 0, 0])
        g.step("ASK: water")
        self.assertTrue(g.pending_check)
        g.step("GUESS: cat")
        self.assertEqual(g.result()["low_probability_opportunities"], 1)
        self.assertEqual(g.result()["reasks_after_low_probability"], 0)

    def test_model_token_classes_are_logged_separately(self):
        g = Game(example())
        g.step(
            "ASK: fur",
            reasoning_tokens=7,
            action_tokens=4,
            predicate_tokens=1,
            truncated=True,
        )
        self.assertEqual(g.result()["reasoning_tokens"], 7)
        self.assertEqual(g.result()["action_tokens"], 4)
        self.assertEqual(g.result()["truncation_count"], 1)

    def test_prompt_never_contains_target_or_private_posterior(self):
        a = example()
        b = example()
        b["target"] = 2
        self.assertEqual(messages(a), messages(b))


class WorldTests(unittest.TestCase):
    def test_duplicate_vectors_and_names_rejected(self):
        for names, rows in [(("a", "b"), [[0], [0]]), (("a", "a"), [[0], [1]])]:
            with self.assertRaises(ValueError):
                World("x", ("attr",), names, np.array(rows))

    def test_bad_dimensions_and_nonbinary_rejected(self):
        with self.assertRaises(ValueError):
            World("x", ("attr",), ("a",), np.array([[2]]))
        with self.assertRaises(ValueError):
            World("x", ("attr",), ("a",), np.array([[0, 1]]))

    def test_constant_attributes_dropped_and_rows_unique(self):
        w = World("x", ("constant", "varies"), ("a", "b"), np.array([[1, 0], [1, 1]]))
        self.assertEqual(w.subset([1, 0]).attributes, ("varies",))
        with self.assertRaises(ValueError):
            w.subset([0, 0])

    def test_all_worlds_and_training_split(self):
        for domain in ["animals", "tools", "foods", "synthetic"]:
            w = load_world(domain)
            self.assertGreaterEqual(len(w.names), 300)
        split = load_split()
        self.assertEqual(len(split["train"]), 200)
        self.assertFalse(set(split["train"]) & set(split["held_out"]))
        self.assertEqual(
            set(split["train"]) | set(split["held_out"]),
            set(load_world("animals").names),
        )

    def test_paid_animals_are_held_out_rows(self):
        r = sample_game("animals", 128, 0, namespace="paid-v1", noise=0)
        self.assertTrue(set(r["world"]["names"]) <= set(load_split()["held_out"]))

    def test_training_factory_enforces_pool_and_sizes(self):
        r = training_game(128, 0, seed=11, noise=0.1)
        self.assertEqual(r["domain"], "animals")
        self.assertTrue(set(r["world"]["names"]) <= set(load_split()["train"]))
        self.assertFalse(set(r["world"]["names"]) & set(load_split()["held_out"]))
        with self.assertRaises(ValueError):
            training_game(256, 0, seed=11, noise=0)

    def test_subsets_reproduce_and_synthetic_labels_change(self):
        a = sample_game("synthetic", 256, 0, namespace="paid-v1", noise=0)
        b = sample_game("synthetic", 256, 0, namespace="paid-v1", noise=0.1)
        self.assertEqual(a["world"], b["world"])
        self.assertEqual(a["target"], b["target"])
        c = sample_game("synthetic", 256, 1, namespace="paid-v1", noise=0)
        self.assertFalse(set(a["world"]["attributes"]) & set(c["world"]["attributes"]))


if __name__ == "__main__":
    unittest.main()
