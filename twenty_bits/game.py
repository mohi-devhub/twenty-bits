"""Exact scripted game transitions and behavior logs shared by every player."""

from __future__ import annotations
import math
import random
from .information import entropy, expected_gain, update
from .predicates import ParseError, lex, parse
from .worlds import World
from .attributes import attribute_aliases
import numpy as np

LOW_PROBABILITY = 0.20
CONFIDENCE = 0.95


class Game:
    def __init__(self, record: dict, *, grammar_version="attribute-codes-v2"):
        self.record = record
        self.world = World.from_dict(record["world"])
        if grammar_version not in {"names-v1", "attribute-codes-v2"}:
            raise ValueError("Unknown grammar version.")
        self.grammar_version = grammar_version
        self.aliases = (
            attribute_aliases(self.world.attributes)
            if grammar_version == "attribute-codes-v2"
            else {}
        )
        self.target = record["target"]
        self.noise = record["noise"]
        if self.noise not in (0, 0.10) or not 0 <= self.target < len(self.world.names):
            raise ValueError("Invalid game target or noise level.")
        self.limit = 2 * math.ceil(math.log2(len(self.world.names)))
        self.posterior = np.full(len(self.world.names), 1 / len(self.world.names))
        rng = random.Random(record["noise_seed"])
        self.flips = [rng.random() < self.noise for _ in range(self.limit)]
        self.turns = []
        self.questions = 0
        self.done = False
        self.won = False
        self.reward = 0.0
        self.pending_check = False
        self.used_masks: list[np.ndarray] = []

    def step(
        self,
        action: str,
        *,
        reasoning_tokens: int = 0,
        action_tokens: int = 0,
        predicate_tokens: int | None = None,
        truncated: bool = False,
    ) -> dict:
        if self.done:
            raise ValueError("The game has ended.")
        raw_action = action
        action = action.strip()
        before = self.posterior.copy()
        turn = {
            "action": action,
            "raw_action": raw_action,
            "question_index": self.questions,
            "eig": 0.0,
            "realized_bits": 0.0,
            "invalid": False,
            "format_error": False,
            "enumeration": False,
            "named_items": 0,
            "predicate_grammar_tokens": 0,
            "predicate_tokens": predicate_tokens,
            "reasoning_tokens": reasoning_tokens,
            "action_tokens": action_tokens,
            "truncated": truncated,
            "after_low_probability": self.pending_check,
            "reask_after_low_probability": False,
            "reask": False,
            "low_probability_answer": False,
            "posterior_before": before.tolist(),
            "entropy_before": entropy(before),
        }
        if self.questions >= self.limit and not action.startswith("GUESS: "):
            self.done = True
            turn.update(
                answer="LOSS",
                is_question=False,
                format_error=True,
                forced_end="Only a final guess is allowed after the question budget.",
            )
        elif action.startswith("GUESS: "):
            self.won = action[7:].strip() == self.world.names[self.target]
            self.done = True
            self.reward += float(self.won)
            turn["answer"] = "WIN" if self.won else "LOSS"
            turn["is_question"] = False
        else:
            self.questions += 1
            self.reward -= 0.03
            turn["is_question"] = True
            try:
                if not action.startswith("ASK: ") or "\n" in action:
                    turn["format_error"] = True
                    raise ParseError("Expected one ASK or GUESS line.")
                if self.questions > self.limit:
                    raise ParseError(
                        "Only a final guess is allowed after the question budget."
                    )
                text = action[5:].strip()
                expression = parse(text, aliases=self.aliases)
                mask = expression.evaluate(
                    self.world.attributes,
                    self.world.names,
                    self.world.rows,
                    aliases=self.aliases,
                )
                turn["enumeration"] = expression.named_items > 0
                turn["named_items"] = expression.named_items
                turn["predicate_grammar_tokens"] = len(lex(text))
                turn["eig"] = float(expected_gain(before, mask, self.noise))
                turn["reask"] = any(
                    np.array_equal(mask, old) or np.array_equal(mask, ~old)
                    for old in self.used_masks
                )
                turn["reask_after_low_probability"] = bool(
                    self.pending_check and turn["reask"]
                )
                self.used_masks.append(mask)
                truth = bool(mask[self.target])
                flipped = self.flips[self.questions - 1]
                answer = truth != flipped
                yes_probability = self.noise + (1 - 2 * self.noise) * float(
                    mask @ before
                )
                received_probability = (
                    yes_probability if answer else 1 - yes_probability
                )
                self.pending_check = received_probability < LOW_PROBABILITY
                turn.update(
                    answer="YES" if answer else "NO",
                    truthful_answer=truth,
                    flipped=flipped,
                    answer_probability=received_probability,
                    low_probability_answer=self.pending_check,
                )
                self.posterior = update(before, mask, answer, self.noise)
                turn["realized_bits"] = entropy(before) - entropy(self.posterior)
            except ParseError as exc:
                turn.update(answer="INVALID", invalid=True, error=str(exc))
                self.reward -= 0.1
                self.pending_check = False
            if self.questions > self.limit:
                self.done = True
        turn["posterior_after"] = self.posterior.tolist()
        turn["entropy_after"] = entropy(self.posterior)
        turn["questions_used"] = self.questions
        self.turns.append(turn)
        return turn

    def result(self) -> dict:
        questions = [t for t in self.turns if t["is_question"]]
        opportunities = [t for t in self.turns if t["after_low_probability"]]
        return {
            "game_id": self.record["id"],
            "domain": self.record["domain"],
            "n": len(self.world.names),
            "noise": self.noise,
            "won": self.won,
            "questions": self.questions,
            "reward": self.reward,
            "eig_per_question": float(np.mean([t["eig"] for t in questions]))
            if questions
            else None,
            "win_bits_per_question": math.log2(len(self.world.names)) / self.questions
            if self.won and self.questions
            else None,
            "invalid_count": sum(t["invalid"] for t in questions),
            "format_error_count": sum(t["format_error"] for t in self.turns),
            "truncation_count": sum(t["truncated"] for t in self.turns),
            "early_guess": any(
                not t["is_question"]
                and t["questions_used"] < math.ceil(math.log2(len(self.world.names)))
                for t in self.turns
            ),
            "singleton_enumeration_questions": sum(
                t["named_items"] == 1 for t in questions
            ),
            "large_name_list_questions": sum(
                t["named_items"] >= len(self.world.names) / 4 for t in questions
            ),
            "enumeration_count": sum(t["enumeration"] for t in questions),
            "predicate_grammar_tokens": sum(
                t["predicate_grammar_tokens"] for t in questions
            ),
            "low_probability_opportunities": len(opportunities),
            "reasks_after_low_probability": sum(
                t["reask_after_low_probability"] for t in opportunities
            ),
            "question_eigs": [t["eig"] for t in questions],
            "reasoning_tokens": sum(t["reasoning_tokens"] for t in self.turns),
            "action_tokens": sum(t["action_tokens"] for t in self.turns),
        }
