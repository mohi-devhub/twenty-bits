"""Random and exact greedy policies, with a declared Bayesian confirmation rule."""

from __future__ import annotations
import random
import numpy as np
from .game import CONFIDENCE, Game
from .information import expected_gain


class Baseline:
    def __init__(self, game: Game, kind: str, seed: int):
        self.kind = kind
        self.rng = random.Random(seed)
        attrs = game.world.attributes
        columns = game.world.rows.T.astype(bool)
        texts = list(attrs)
        masks = list(columns)
        if kind == "greedy_predicate":
            # OR is the complement of an AND of complemented literals. EIG
            # is unchanged by complement, so these four conjunctions cover
            # every two-attribute AND/OR/NOT split without duplicate scoring.
            for i in range(len(attrs)):
                for j in range(i + 1, len(attrs)):
                    for neg_a, neg_b in [
                        (False, False),
                        (False, True),
                        (True, False),
                        (True, True),
                    ]:
                        a = ~columns[i] if neg_a else columns[i]
                        b = ~columns[j] if neg_b else columns[j]
                        masks.append(a & b)
                        texts.append(
                            f"({'NOT ' if neg_a else ''}{attrs[i]} AND {'NOT ' if neg_b else ''}{attrs[j]})"
                        )
        self.texts = texts
        self.masks = np.asarray(masks, dtype=float)

    def act(self, game: Game) -> str:
        top = int(np.argmax(game.posterior))
        if game.questions >= game.limit or float(game.posterior[top]) >= (
            CONFIDENCE if game.noise else 1 - 1e-12
        ):
            return "GUESS: " + game.world.names[top]
        if self.kind == "random":
            return (
                "ASK: "
                + game.world.attributes[self.rng.randrange(len(game.world.attributes))]
            )
        if self.kind == "greedy_predicate" and game.noise and game.pending_check:
            # One immediate confirmation of the question that produced an
            # unlikely answer. A further unlikely reply can trigger another.
            previous = game.turns[-1]
            if previous["is_question"] and not previous["invalid"]:
                return previous["action"]
        gains = expected_gain(game.posterior, self.masks, game.noise)
        return "ASK: " + self.texts[int(np.argmax(gains))]


def play(record: dict, kind: str, *, tokenizer=None, keep_trace: bool = False) -> dict:
    game = Game(record)
    policy = Baseline(game, kind, record["noise_seed"] ^ 191)
    for _ in range(game.limit + 1):
        action = policy.act(game)
        predicate_tokens = (
            len(tokenizer.encode(action[5:], add_special_tokens=False))
            if tokenizer is not None and action.startswith("ASK: ")
            else None
        )
        action_tokens = (
            len(tokenizer.encode(action, add_special_tokens=False))
            if tokenizer is not None
            else 0
        )
        game.step(
            action, action_tokens=action_tokens, predicate_tokens=predicate_tokens
        )
        if game.done:
            break
    if not game.done:
        raise RuntimeError("Baseline failed to finish within the action budget.")
    result = game.result()
    result["policy"] = kind
    result["predicate_tokens"] = sum(t["predicate_tokens"] or 0 for t in game.turns)
    if keep_trace:
        result["record"] = record
        result["turns"] = game.turns
    return result
