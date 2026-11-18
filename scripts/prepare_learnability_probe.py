"""Freeze the approved 32-game training-pool probe and prove rendering offline."""

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.budget import MULTIPLIER, money
from twenty_bits.game import Game
from twenty_bits.learnability import (
    PROMPT_VERSION,
    probe_messages,
    probe_records,
    prompt_examples,
)
from twenty_bits.predicates import parse
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import sample_cost
from twenty_bits.worlds import ROOT, World, load_split


def main():
    config = json.loads((ROOT / "evals/phase2.json").read_text())
    config.update(
        run_id="learnability-probe-v1",
        approval_date="2026-11-18",
        prompt_version=PROMPT_VERSION,
        active_models=[config["primary_model"]],
        display_name="Twenty Bits prompt learnability probe",
        run_cap_usd="1.500000",
        training_authorized=False,
        sizes=[8, 16],
        games_per_size=16,
        noise=0,
        remaining_candidate_feedback=False,
        concurrent_games=4,
        sampling_seed_namespace="learnability-probe-policy-v1",
    )
    directory = ROOT / "experiments"
    directory.mkdir(exist_ok=True)
    config_path = directory / "learnability_probe.json"
    records = probe_records()
    records_path = directory / "learnability_probe_games.json"
    for path, value in [(config_path, config), (records_path, records)]:
        if path.exists() and json.loads(path.read_text()) != value:
            raise RuntimeError("The prepared probe settings or games changed.")
        path.write_text(json.dumps(value, indent=2) + "\n")
    rendering = Rendering(config["primary_model"], config)
    checks = []
    envelope = Decimal(0)
    train_names = set(load_split()["train"])
    for record in records:
        world = World.from_dict(record["world"])
        assert set(world.names) <= train_names
        assert not set(world.names) & set(load_split()["held_out"])
        game = Game(record)
        initial = rendering.prompt(probe_messages(record, [])).length
        history_checks = []
        # Exercise prompt parity and valid random examples through a full game.
        for i in range(game.limit):
            action = prompt_examples(world)[i % 3]
            parse(action[5:]).evaluate(world.attributes, world.names, world.rows)
            game.step(action)
            history_checks.append(
                rendering.prompt(probe_messages(record, game.turns)).length
            )
        for i in range(game.limit + 1):
            # 64 tokens safely covers chat framing and the one-word answer.
            prompt_bound = initial + (config["primary_output_cap"] + 64) * i
            if prompt_bound + config["primary_output_cap"] > config["context_window"]:
                raise RuntimeError(
                    "The full-cap probe cannot fit its declared context."
                )
            estimate = money(sample_cost(config["primary_model"], prompt_bound, 64))
            maximum = money(
                sample_cost(
                    config["primary_model"], prompt_bound, config["primary_output_cap"]
                )
            )
            envelope += max(money(estimate * MULTIPLIER), maximum)
        public = probe_messages(record)
        checks.append(
            {
                "id": record["id"],
                "initial_prompt_tokens": initial,
                "history_prompt_tokens": history_checks,
                "public_messages_sha256": hashlib.sha256(
                    json.dumps(public, sort_keys=True).encode()
                ).hexdigest(),
            }
        )
    if envelope > money(config["run_cap_usd"]):
        raise RuntimeError("The sum of full-cap call holds would exceed $1.50.")
    proof = {
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "games_sha256": hashlib.sha256(records_path.read_bytes()).hexdigest(),
        "prompt_code_sha256": hashlib.sha256(
            (ROOT / "twenty_bits/learnability.py").read_bytes()
        ).hexdigest(),
        "model": config["primary_model"],
        "service_calls": 0,
        "cookbook_native_parity": True,
        "all_train_pool": True,
        "full_cap_hold_envelope_usd": str(envelope),
        "checks": checks,
    }
    (ROOT / "research/learnability_probe_rendering.json").write_text(
        json.dumps(proof, indent=2) + "\n"
    )
    print(json.dumps({k: v for k, v in proof.items() if k != "checks"}, indent=2))


if __name__ == "__main__":
    main()
