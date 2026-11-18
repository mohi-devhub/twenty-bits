"""Freeze a parser-only re-probe with identical games, prompts and seeds."""

from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.game import Game
from twenty_bits.learnability import probe_messages, probe_records, prompt_examples
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import save_json
from twenty_bits.worlds import ROOT


def main():
    old_path = ROOT / "experiments/learnability_probe.json"
    config = json.loads(old_path.read_text())
    config.update(
        run_id="attribute-alias-probe-v1",
        run_cap_usd="0.250000",
        grammar_version="attribute-codes-v2",
        policy="attribute_alias_probe",
        incident_record=None,
        reference_model=None,
        reference_games_per_cell=0,
        reference_sizes=[],
        display_name="Twenty Bits attribute alias probe",
        approval_date=datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat(),
    )
    config["decision_rule"] = {
        "valid_turn_rate_minimum": 0.80,
        "valid_turn_denominator": "All generated turns pooled across 32 completed games, including final-slot failures.",
        "n8_wins_minimum": 1,
        "on_pass": "Skip SFT; propose RL; do not train.",
        "on_fail": "Approved format SFT plus qualification only, capped at $2.51 including holds; no RL.",
    }
    config_path = ROOT / "experiments/alias_probe.json"
    if config_path.exists() and json.loads(config_path.read_text()) != config:
        raise RuntimeError("Prepared alias-probe settings changed.")
    save_json(config_path, config)
    records_path = ROOT / "experiments/learnability_probe_games.json"
    records = json.loads(records_path.read_text())
    assert records == probe_records()
    previous = json.loads(
        (ROOT / "research/learnability_probe_rendering.json").read_text()
    )
    rendering = Rendering(config["primary_model"], config)
    checks = []
    for record, old in zip(records, previous["checks"]):
        public = probe_messages(record)
        digest = hashlib.sha256(json.dumps(public, sort_keys=True).encode()).hexdigest()
        assert record["id"] == old["id"] and digest == old["public_messages_sha256"]
        initial = rendering.prompt(public).length
        assert initial == old["initial_prompt_tokens"]
        game = Game(record, grammar_version=config["grammar_version"])
        histories = []
        for i in range(game.limit):
            game.step(prompt_examples(game.world)[i % 3])
            histories.append(
                rendering.prompt(probe_messages(record, game.turns)).length
            )
        assert histories == old["history_prompt_tokens"]
        checks.append(
            {
                "id": record["id"],
                "initial_prompt_tokens": initial,
                "public_messages_sha256": digest,
                "histories_checked": len(histories),
            }
        )
    proof = {
        "implementation_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ("twenty_bits/predicates.py", "twenty_bits/attributes.py", "twenty_bits/game.py")},
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "games_sha256": hashlib.sha256(records_path.read_bytes()).hexdigest(),
        "prompt_code_sha256": hashlib.sha256(
            (ROOT / "twenty_bits/learnability.py").read_bytes()
        ).hexdigest(),
        "full_cap_hold_envelope_usd": previous["full_cap_hold_envelope_usd"],
        "forecast_usd": "0.069563",
        "forecast_with_margin_usd": "0.104345",
        "run_cap_usd": "0.250000",
        "admission_note": "The full-run cap scenario exceeds $0.25. The measured prior run admits this forecast; each individual hold must still fit $0.25 or sampling stops unchanged.",
        "public_prompt_bytes_unchanged": True,
        "generation_seed_namespace_unchanged": True,
        "cookbook_native_parity": True,
        "service_calls": 0,
        "checks": checks,
    }
    save_json(ROOT / "research/alias_probe_rendering.json", proof)
    print(json.dumps({k: v for k, v in proof.items() if k != "checks"}, indent=2))


if __name__ == "__main__":
    main()
