"""Run two paired, inference-only candidate-set checks, capped at $0.50 total."""

import asyncio
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.run_learnability_probe import main as run_probe
from twenty_bits.candidate_feedback import candidate_messages
from twenty_bits.supervised import qualification_records
from twenty_bits.tinker_transport import save_json
from twenty_bits.worlds import ROOT

POLICIES = ("format_sft", "raw_base")


async def main():
    # The SFT checkpoint is loaded for inference only. Never create/train a LoRA.
    for policy in POLICIES:
        config_path = ROOT / f"experiments/candidate_set_{policy}.json"
        config = json.loads(config_path.read_text())
        if (
            config["training_authorized"]
            or config["run_cap_usd"] != "0.250000"
            or config["policy"] != policy
        ):
            raise RuntimeError("Only the approved two inference slices may run.")
        proof_path = ROOT / f"research/candidate_set_{policy}_rendering.json"
        await run_probe(
            config_path=config_path,
            proof_path=proof_path,
            games_path=ROOT / "experiments/format_qualification_games.json",
            results_path=ROOT / f"results/candidate_set/{policy}",
            approved_run_cap="0.250000",
            records_factory=qualification_records,
            message_builder=candidate_messages,
        )
        directory = ROOT / "runs" / config["run_id"]
        games = list((directory / "games").glob("*.json"))
        if len(games) != 32:
            raise RuntimeError("Candidate qualification is incomplete; stop.")
        state = json.loads((directory / "sessions.json").read_text())
        save_json(
            ROOT / f"results/candidate_set/{policy}/completion.json",
            {
                "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
                "games": 32,
                "sampler": state["samplers"][config["primary_model"]],
                "session_finished": state["finished"],
                "training_updates": 0,
                "rl_updates": 0,
            },
        )


if __name__ == "__main__":
    asyncio.run(main())
