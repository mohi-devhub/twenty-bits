"""Save illustrative matched baseline games in the model-ready replay schema."""

from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from threadpoolctl import threadpool_limits
from twenty_bits.worlds import ROOT, sample_game
from twenty_bits.baselines import play
from twenty_bits.prompts import get_tokenizer


def main():
    pairs = []
    with threadpool_limits(limits=1):
        for noise in [0, 0.1]:
            for i in range(100):
                record = sample_game(
                    "animals", 16, i, namespace="replay-v1", noise=noise
                )
                left = play(
                    record, "random", tokenizer=get_tokenizer(), keep_trace=True
                )
                right = play(
                    record,
                    "greedy_predicate",
                    tokenizer=get_tokenizer(),
                    keep_trace=True,
                )
                checks = right["reasks_after_low_probability"]
                if right["won"] and not left["won"] and (not noise or checks):
                    pairs.append(
                        {
                            "label": "Noisy answers" if noise else "Truthful answers",
                            "record": record,
                            "players": [
                                {"label": "Random attribute", "trace": left},
                                {"label": "Greedy predicate", "trace": right},
                            ],
                            "selection": "Illustrative contrast: greedy wins, random loses; noisy example includes a re-check. Not an unbiased performance sample.",
                        }
                    )
                    break
            else:
                raise RuntimeError("No suitable replay found.")
    content = json.dumps(pairs, separators=(",", ":"))
    (ROOT / "replays/games.json").write_text(json.dumps(pairs, indent=2) + "\n")
    (ROOT / "replays/games.js").write_text("window.REPLAYS = " + content + ";\n")
    print([(p["label"], p["record"]["id"]) for p in pairs])


if __name__ == "__main__":
    main()
