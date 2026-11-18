"""Prepare and price a possible format warm start offline. No training occurs."""

from decimal import Decimal
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.game import Game
from twenty_bits.learnability import probe_messages
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import rates
from twenty_bits.worlds import ROOT, World, seed_for


def toy_record(n, index):
    rng = random.Random(seed_for("format-toy-proposal-v1", n, index))
    probabilities = [0.05, 0.10, 0.20, 0.35, 0.65, 0.80, 0.90, 0.95] * 2
    rng.shuffle(probabilities)
    rows = []
    while len(rows) < n:
        row = tuple(int(rng.random() < p) for p in probabilities)
        if row not in rows:
            rows.append(row)
    matrix = np.asarray(rows, dtype=np.uint8)
    world = World(
        "format_toy",
        tuple(f"property_{rng.randrange(10**8, 10**9)}" for _ in range(16)),
        tuple(f"object_{rng.randrange(10**8, 10**9)}" for _ in range(n)),
        matrix,
    ).subset(list(range(n)))
    return {
        "id": f"format-toy-proposal-v1/{n}/{index}",
        "domain": "format_toy",
        "n": n,
        "world": world.to_dict(),
        "target": rng.randrange(n),
        "noise": 0,
        "noise_seed": seed_for("format-toy-noise-v1", n, index),
    }


def main():
    config = json.loads((ROOT / "experiments/learnability_probe.json").read_text())
    rendering = Rendering(config["primary_model"], config)
    examples, games, token_lengths = [], [], []
    for n in (4, 8):
        for index in range(64):
            record = toy_record(n, index)
            game = Game(record)
            rng = random.Random(seed_for("format-random-attributes-v1", n, index))
            actions = []
            while not game.done:
                certain = np.count_nonzero(game.posterior) == 1
                if not certain and game.questions >= game.limit:
                    break  # No target-oracle guess on an ambiguous trajectory.
                action = (
                    "GUESS: " + game.world.names[int(np.argmax(game.posterior))]
                    if certain
                    else "ASK: " + rng.choice(game.world.attributes)
                )
                public = probe_messages(record, game.turns)
                prompt = rendering.prompt(public).to_ints()
                tokens, weights = rendering.renderer.build_supervised_example(
                    public + [{"role": "assistant", "content": action}]
                )
                token_ids = tokens.to_ints()
                if token_ids[: len(prompt)] != prompt:
                    raise RuntimeError(
                        "Warm-start supervision differs from the sampled prefix."
                    )
                if any(weights[: len(prompt)]):
                    raise RuntimeError("Prompt tokens received supervision weight.")
                examples.append(
                    {
                        "game_id": record["id"],
                        "turn": len(game.turns),
                        "messages": public + [{"role": "assistant", "content": action}],
                        "train_on": "last_assistant_message",
                    }
                )
                token_lengths.append(tokens.length - 1)
                turn = game.step(action)
                assert not turn["invalid"]
                actions.append(action)
            games.append(
                {
                    "id": record["id"],
                    "n": n,
                    "won": game.won,
                    "actions": actions,
                    "guesses_only_at_singleton": True,
                }
            )
    raw = "".join(
        json.dumps(e, separators=(",", ":")) + "\n" for e in examples
    ).encode()
    path = ROOT / "experiments/format_warmstart_proposal.jsonl.gz"
    path.write_bytes(gzip.compress(raw, mtime=0))
    total = sum(token_lengths)
    r = rates(config["primary_model"])
    epochs = 2
    train_cost = Decimal(total * epochs) * r["train"] / 1_000_000
    result = {
        "authorized": False,
        "service_calls": 0,
        "model": config["primary_model"],
        "procedural_games": len(games),
        "examples": len(examples),
        "question_policy": "Uniform single attributes with replacement; independent of target, posterior and split quality.",
        "column_probabilities": "Two copies of [.05, .10, .20, .35, .65, .80, .90, .95], shuffled per game. Constant columns are dropped. Random questions are not selected for balance.",
        "guess_policy": "Correct GUESS only when posterior support has one item. Ambiguous games contribute questions and no guess.",
        "domain_caveat": "These separate procedural toy tables contain no frozen or held-out world rows. Using them for SFT would nevertheless expose the model to random-table identification. Synthetic transfer would then mean new tables, labels and sizes, rather than an unseen random-table task.",
        "supervised_behavior_caveat": "This also teaches stopping and table/answer tracking at singleton. It does not demonstrate bisection.",
        "epochs": epochs,
        "batches_of_32_examples": math.ceil(len(examples) / 32) * epochs,
        "full_context_tokens_per_epoch": total,
        "longest_example_tokens": max(token_lengths),
        "forward_backward_usd": str(train_cost),
        "forward_backward_with_margin_usd": str(train_cost * Decimal("1.5")),
        "storage_allowance_usd": "0.100000",
        "total_with_storage_and_margin_usd": str(
            (train_cost + Decimal(".1")) * Decimal("1.5")
        ),
        "data_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "games": games,
    }
    (ROOT / "research/format_warmstart_price.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "games"}, indent=2))


if __name__ == "__main__":
    main()
