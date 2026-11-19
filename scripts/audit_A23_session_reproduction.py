"""Check supplied seeds and observed variation using saved responses only."""

import gzip
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.tinker_transport import save_json
from twenty_bits.worlds import ROOT


def rows(path):
    return [json.loads(line) for line in gzip.open(ROOT / path, "rt")]


def main():
    primary = {g["game_id"]: g for g in rows("results/main_A23/games.jsonl.gz")
               if g["kind"] == "eval_endpoint" and g["domain"] == "synthetic"}
    auxiliary = rows("results/A23_suffix/games.jsonl.gz")
    requests = {r["entry_id"]: r for filename in (
        "results/main_A23/requests.jsonl.gz", "results/A23_suffix/requests.jsonl.gz",
        "results/A23_hard/requests.jsonl.gz") for r in rows(filename)}
    checked = 0
    identical = 0
    pre_mapping = []
    post_mapping = []
    for game in sorted(auxiliary, key=lambda g: g["game_id"]):
        original = primary[game["game_id"]]
        mapped = False
        divergence = None
        for index, (before, after) in enumerate(zip(original["turns"], game["turns"])):
            p = requests[before["usage"]["entry_id"]]["parameters"]
            q = requests[after["usage"]["entry_id"]]["parameters"]
            assert p == q, (game["game_id"], index)
            checked += 1
            if divergence is None and before["raw_action"] != after["raw_action"]:
                same_prompt = original["trajectory"][index]["ob"] == game["trajectory"][index]["ob"]
                divergence = {"game_id": game["game_id"], "turn_index": index,
                    "same_prompt_tokens": same_prompt, "same_supplied_parameters": True,
                    "earlier_suffix_mapping": mapped}
                if not mapped:
                    assert same_prompt
                    pre_mapping.append(divergence)
                else:
                    post_mapping.append(divergence)
            mapped = mapped or bool(after.get("suffix_mappings"))
        identical += divergence is None and len(original["turns"]) == len(game["turns"])
    hard = rows("results/A23_hard/games.jsonl.gz")
    base = {g["game_id"]: g for g in hard if g["policy"] == "raw_base"}
    hard_checked = 0
    for game in hard:
        if game["policy"] == "raw_base":
            continue
        for before, after in zip(base[game["game_id"]]["turns"], game["turns"]):
            assert requests[before["usage"]["entry_id"]]["parameters"] == requests[after["usage"]["entry_id"]]["parameters"]
            hard_checked += 1
    result = {"service_calls": 0, "paired_synthetic_games": len(auxiliary),
        "shared_turn_parameter_checks": checked, "hard_mode_shared_turn_parameter_checks": hard_checked,
        "supplied_parameter_mismatches": 0, "identical_complete_action_pairs": identical,
        "initial_action_divergence_before_mapping": pre_mapping,
        "initial_action_divergence_after_mapping": post_mapping,
        "interpretation": f"{len(pre_mapping)} pairs differ in action before any parser mapping despite identical prompt tokens and supplied sampling parameters, including seed. The backend/restore cause is unestablished. These fresh diagnostic rollouts contain session reproduction variation, so small score differences cannot all be attributed to parser tolerance. Primary scores and rewards are unchanged."}
    save_json(ROOT / "results/A23_suffix/session_variation.json", result)
    print(json.dumps({key: value for key, value in result.items() if not isinstance(value, list)}, indent=2))


if __name__ == "__main__":
    main()
