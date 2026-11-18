"""Replay both candidate-set policies and compare paired development outcomes."""

from collections import Counter, defaultdict
from contextlib import redirect_stdout
from decimal import Decimal
import gzip
import io
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.audit_qualification import audit
from scripts.summarize_learnability_probe import main as summarize_probe
from twenty_bits.budget import Ledger
from twenty_bits.candidate_feedback import candidate_messages, feedback, token_hash
from twenty_bits.learnability import probe_messages
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import sample_cost, save_json
from twenty_bits.worlds import ROOT


def read_games(folder):
    return [json.loads(line) for line in gzip.open(folder / "games.jsonl.gz", "rt")]


def paired_comparison(a, b, sizes):
    rng = np.random.default_rng(20261118)
    indices = np.concatenate(
        [
            rng.choice(np.flatnonzero(np.asarray(sizes) == n), (10000, sizes.count(n)))
            for n in sorted(set(sizes))
        ],
        axis=1,
    )

    def values(gs, sample):
        won = np.asarray([g["won"] for g in gs], dtype=float)
        q = np.asarray([g["questions"] for g in gs], dtype=float)
        e = np.asarray([sum(g["question_eigs"]) for g in gs])
        return {
            "win_rate": won[sample].mean(axis=-1),
            "eig_per_question": np.divide(
                e[sample].sum(axis=-1),
                q[sample].sum(axis=-1),
                out=np.full(np.shape(q[sample].sum(axis=-1)), np.nan),
                where=q[sample].sum(axis=-1) > 0,
            ),
        }

    av, bv = values(a, indices), values(b, indices)
    ap, bp = values(a, np.arange(len(a))), values(b, np.arange(len(b)))
    return {
        name: {
            "sft_minus_raw_base": float(ap[name] - bp[name]),
            "paired_ci95": np.nanquantile(av[name] - bv[name], [0.025, 0.975]).tolist(),
        }
        for name in av
    }


def main():
    root = ROOT / "results/candidate_set"
    records = {
        r["id"]: r
        for r in json.loads(
            (ROOT / "experiments/format_qualification_games.json").read_text()
        )
    }
    policies, games = {}, {}
    combined_spent = combined_held = Decimal(0)
    for policy in ("format_sft", "raw_base"):
        path = ROOT / f"experiments/candidate_set_{policy}.json"
        config = json.loads(path.read_text())
        folder = root / policy
        with redirect_stdout(io.StringIO()):
            summarize_probe(
                config_path=path,
                games_path=ROOT / "experiments/format_qualification_games.json",
                output_path=folder,
                message_builder=candidate_messages,
            )
        summary = json.loads((folder / "summary.json").read_text())
        gs = sorted(read_games(folder), key=lambda g: g["game_id"])
        games[policy] = gs
        rendering = Rendering(config["primary_model"], config)
        inputs = []
        prompt_hashes = []
        causes = Counter()
        zero_eig = repeated = 0
        full_forecast = Decimal(0)
        for g in gs:
            record = records[g["game_id"]]
            for i, turn in enumerate(g["turns"]):
                public = candidate_messages(record, g["turns"][:i])
                prompt = rendering.prompt(public)
                hard = rendering.prompt(probe_messages(record, g["turns"][:i]))
                latest_state = (
                    feedback(record, g["turns"][i - 1]["posterior_after"])
                    if i
                    else None
                )
                inputs.append(
                    {
                        "game_id": g["game_id"],
                        "n": g["n"],
                        "turn": i,
                        "prompt_tokens": prompt.length,
                        "no_list_tokens": hard.length,
                        "candidates_shown": len(latest_state["candidates"])
                        if i
                        else g["n"],
                        "latest_feedback_tokens": len(
                            rendering.tokenizer.encode(
                                public[-1]["content"].split("\n", 1)[1],
                                add_special_tokens=False,
                            )
                        )
                        if i
                        else 0,
                    }
                )
                prompt_hashes.append(
                    {
                        "game_id": g["game_id"],
                        "turn": i,
                        "prompt_tokens_sha256": token_hash(prompt.to_ints()),
                        "request_id": turn["usage"]["request_id"],
                    }
                )
                full_forecast += Decimal(
                    sample_cost(
                        config["primary_model"],
                        prompt.length,
                        turn["usage"]["output_tokens"],
                    )
                )
                zero_eig += (
                    turn["is_question"] and not turn["invalid"] and turn["eig"] < 1e-12
                )
                repeated += turn["reask"]
            if g["won"]:
                continue
            last = g["turns"][-1]
            if last["action"].startswith("GUESS: "):
                guess = last["action"][7:].strip()
                names = record["world"]["names"]
                if guess not in names:
                    causes["guess_outside_table"] += 1
                elif last["posterior_before"][names.index(guess)] == 0:
                    causes["guess_of_eliminated_item"] += 1
                else:
                    causes["wrong_guess_among_remaining_candidates"] += 1
            else:
                causes["no_final_guess_after_budget"] += 1
        assert sum(causes.values()) == 32 - sum(g["won"] for g in gs)
        by_turn = defaultdict(list)
        for row in inputs:
            by_turn[row["n"], row["turn"]].append(row)
        costs = summary["cost"]
        combined_spent += Decimal(costs["probe_spent_usd"])
        combined_held += Decimal(costs["probe_held_usd"])
        summary.update(
            policy=policy,
            behavior_audit=audit(gs, records),
            loss_causes=dict(causes),
            valid_zero_eig_questions=int(zero_eig),
            repeated_splits=int(repeated),
            token_measurements={
                "uncached_observed_trajectory_forecast_usd": str(full_forecast),
                "extra_input_tokens_vs_no_list_same_actions": sum(
                    x["prompt_tokens"] - x["no_list_tokens"] for x in inputs
                ),
                "by_turn": [
                    {
                        "n": n,
                        "turn": t,
                        "games": len(rows),
                        "mean_prompt_tokens": float(
                            np.mean([x["prompt_tokens"] for x in rows])
                        ),
                        "mean_latest_feedback_tokens": float(
                            np.mean([x["latest_feedback_tokens"] for x in rows])
                        ),
                        "mean_candidates_shown": float(
                            np.mean([x["candidates_shown"] for x in rows])
                        ),
                    }
                    for (n, t), rows in sorted(by_turn.items())
                ],
                "interpretation": "Counterfactual no-list counts hold actions fixed; they measure token overhead, not policy performance without feedback. Later-turn averages are conditional on games still running.",
            },
        )
        save_json(folder / "prompt_hashes.json", prompt_hashes)
        save_json(folder / "token_counts.json", inputs)
        save_json(folder / "analysis.json", summary)
        policies[policy] = summary
    assert [g["game_id"] for g in games["format_sft"]] == [
        g["game_id"] for g in games["raw_base"]
    ]
    assert combined_spent + combined_held <= Decimal(".50")
    ledger = Ledger(ROOT / "ledger.json").status()
    result = {
        "complete": True,
        "games_per_policy": 32,
        "total_games": 64,
        "prompt_version": "candidate-set-v1",
        "posterior_threshold": 0.001,
        "policies": policies,
        "paired_comparison": paired_comparison(
            games["format_sft"],
            games["raw_base"],
            [g["n"] for g in games["format_sft"]],
        ),
        "paired_method": "10,000 paired whole-game bootstrap draws, stratified by N, seed 20261118. Development cases only. No independent seed replication.",
        "decision": policies["format_sft"]["decision"],
        "cost": {
            "recorded_usage_usd": str(combined_spent),
            "held_usd": str(combined_held),
            "combined_cap_including_holds_usd": "0.500000",
            "project": {k: ledger[k] for k in ledger if k != "entries"},
        },
        "training_updates": 0,
        "rl_updates": 0,
    }
    save_json(root / "summary.json", result)
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "cost": result["cost"],
                "policies": {
                    p: {
                        "valid_turn_rate": s["pooled_valid_turn_rate"],
                        "wins": s["qualification_wins"],
                        "loss_causes": s["loss_causes"],
                    }
                    for p, s in policies.items()
                },
                "paired_comparison": result["paired_comparison"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
