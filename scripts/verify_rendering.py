"""Prove native/cookbook parity on the approved bank and baseline histories."""

from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.worlds import ROOT
from twenty_bits.evaluation import frozen_games, frozen_manifest
from twenty_bits.baselines import play
from twenty_bits.prompts import prompt_ids
from twenty_bits.tinker_rendering import Rendering


def main():
    path = ROOT / "evals/phase2.json"
    config = json.loads(path.read_text())
    proof = {
        "config_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "cookbook_commit": "6c081121b90dbc290b4550eb9fd9f646f8e4960a",
        "sdk_version": "0.39.1",
        "reference_template_date": config["reference_template_date"],
        "models": [],
        "paid_samples": 0,
    }
    for model in [config["primary_model"], config["reference_model"]]:
        rendering = Rendering(model, config)
        initial = histories = measured_count_matches = 0
        digest = hashlib.sha256()
        for cell in frozen_manifest()["cells"]:
            count = config["primary_games_per_cell"]
            if model == config["reference_model"]:
                if cell["n"] not in config["reference_sizes"]:
                    continue
                count = config["reference_games_per_cell"]
            for record in frozen_games(cell["domain"], cell["n"], cell["noise"], count):
                ids = rendering.observation(record, []).to_ints()
                measured_count_matches += len(ids) == len(
                    prompt_ids(record, model=model)
                )
                digest.update(json.dumps(ids, separators=(",", ":")).encode())
                initial += 1
            for record in frozen_games(cell["domain"], cell["n"], cell["noise"], 2):
                trace = play(record, "greedy_predicate", keep_trace=True)
                for i in range(1, len(trace["turns"])):
                    rendering.observation(record, trace["turns"][:i])
                    histories += 1
                names = record["world"]["names"]
                rendering.observation(
                    record,
                    [
                        {
                            "action": "ASK: "
                            + " OR ".join(
                                "item == " + name for name in names[: len(names) // 2]
                            ),
                            "answer": "YES",
                        }
                    ],
                )
                histories += 1
        proof["models"].append(
            {
                "model": model,
                "initial_prompts_equal": initial,
                "histories_equal": histories,
                "phase1_native_token_counts_equal": measured_count_matches,
                "initial_token_sequences_sha256": digest.hexdigest(),
                "stop_ids": rendering.renderer.get_stop_sequences(),
            }
        )
    (ROOT / config["rendering_proof"]).write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
