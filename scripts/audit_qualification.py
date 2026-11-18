"""Check whether legal guesses agree with the exact noiseless posterior."""

from collections import Counter
import gzip
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.baselines import play
from twenty_bits.worlds import ROOT


def audit(games, records):
    counts = Counter()
    examples = []
    for game in sorted(games, key=lambda g: g["game_id"]):
        record = records[game["game_id"]]
        names = record["world"]["names"]
        singleton = any(
            sum(p > 0 for p in t["posterior_after"]) == 1 for t in game["turns"]
        )
        counts["games_reaching_singleton"] += singleton
        counts["singleton_games_won"] += singleton and game["won"]
        counts["early_guesses"] += game["early_guess"]
        for turn in game["turns"]:
            if not turn["action"].startswith("GUESS: "):
                continue
            counts["guesses"] += 1
            guessed = turn["action"][7:].strip()
            support = [i for i, p in enumerate(turn["posterior_before"]) if p > 0]
            counts["guesses_with_singleton_posterior"] += len(support) == 1
            if guessed not in names:
                counts["guesses_outside_candidate_table"] += 1
                continue
            mass = turn["posterior_before"][names.index(guessed)]
            counts["guesses_of_eliminated_candidates"] += mass == 0
            counts["wrong_guesses_despite_singleton"] += mass == 0 and len(support) == 1
            if game["won"]:
                counts["wins_with_singleton_posterior"] += len(support) == 1
                counts["wins_without_singleton_posterior"] += len(support) != 1
            if mass == 0 and len(support) == 1 and len(examples) < 2:
                examples.append(
                    {
                        "game_id": game["game_id"],
                        "correct_item": names[record["target"]],
                        "remaining_item": names[support[0]],
                        "guess": guessed,
                        "turns": [
                            {"action": t["action"], "answer": t["answer"]}
                            for t in game["turns"]
                        ],
                    }
                )
    return {"counts": dict(counts), "examples": examples}


def main():
    out = ROOT / "results/format_sft"
    games = [json.loads(line) for line in gzip.open(out / "games.jsonl.gz", "rt")]
    records = {
        r["id"]: r
        for r in json.loads(
            (ROOT / "experiments/format_qualification_games.json").read_text()
        )
    }
    result = audit(games, records)
    references = [play(r, "greedy_predicate") for r in records.values()]
    result.update(
        service_calls=0,
        paired_greedy_reference={
            "games": len(references),
            "wins": sum(g["won"] for g in references),
            "mean_questions_per_win": sum(
                g["questions"] for g in references if g["won"]
            )
            / sum(g["won"] for g in references),
            "mean_eig_per_question": sum(sum(g["question_eigs"]) for g in references)
            / sum(g["questions"] for g in references),
        },
        interpretation="Diagnostic observations on development games, not a paid frozen-set comparison. The greedy policy uses only logical consequences of the public table and answers. Selected singleton failures illustrate consistency errors and are not a performance sample.",
    )
    (out / "behavior_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
