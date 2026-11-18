"""Replay pilot samples, audit their gradients, and archive evidence offline."""

from collections import Counter
from decimal import Decimal
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.run_baselines import summarize
from scripts.audit_qualification import audit as consistency_audit
from scripts.run_rl_pilot import game_metrics
from twenty_bits.budget import ACTIVE_STATES, Ledger
from twenty_bits.candidate_feedback import candidate_messages
from twenty_bits.game import Game
from twenty_bits.predicates import parse
from twenty_bits.rl_pilot import group_data, unpack_trajectory
from twenty_bits.tinker_rendering import Rendering
from twenty_bits.tinker_transport import rates, sample_cost, save_json
from twenty_bits.worlds import ROOT, seed_for


def write_gzip(path, rows):
    path.write_bytes(
        gzip.compress(
            "".join(
                json.dumps(r, separators=(",", ":"), allow_nan=False) + "\n"
                for r in rows
            ).encode(),
            mtime=0,
        )
    )


def paired_change(base, final):
    assert [g["game_id"] for g in base] == [g["game_id"] for g in final]
    rng = np.random.default_rng(20261118)
    sizes = np.asarray([g["n"] for g in base])
    indices = np.concatenate(
        [
            rng.choice(np.flatnonzero(sizes == n), (10000, sum(sizes == n)))
            for n in sorted(set(sizes))
        ],
        axis=1,
    )

    def stats(games, idx):
        win = np.array([g["won"] for g in games], dtype=float)
        q = np.array([g["questions"] for g in games], dtype=float)
        e = np.array([sum(g["question_eigs"]) for g in games])
        qs = q[idx].sum(axis=-1)
        return {
            "win_rate": win[idx].mean(axis=-1),
            "eig_per_question": np.divide(
                e[idx].sum(axis=-1), qs, out=np.full(np.shape(qs), np.nan), where=qs > 0
            ),
            "mean_reward": np.array([g["reward"] for g in games])[idx].mean(axis=-1),
        }

    b, f = stats(base, indices), stats(final, indices)
    bp, fp = stats(base, np.arange(len(base))), stats(final, np.arange(len(final)))
    result = {
        k: {
            "final_minus_base": float(fp[k] - bp[k]),
            "ci95": np.nanquantile(f[k] - b[k], [0.025, 0.975]).tolist(),
        }
        for k in b
    }
    changes = [
        f["eig_per_question"] - b["eig_per_question"]
        for b, f in zip(base, final)
        if b["eig_per_question"] is not None and f["eig_per_question"] is not None
    ]
    if changes:
        observed = abs(float(np.mean(changes)))
        null = [
            abs(float(np.mean(np.array(changes) * signs)))
            for signs in itertools.product((-1, 1), repeat=len(changes))
        ]
        result["eig_per_game_exact_paired_permutation"] = {
            "pairs": len(changes),
            "two_sided_p": float(np.mean(np.asarray(null) >= observed - 1e-12)),
            "test_statistic": "mean per-game EIG difference on pairs with defined EIG",
        }
    discordant = [
        int(f["won"]) - int(b["won"])
        for b, f in zip(base, final)
        if f["won"] != b["won"]
    ]
    null = [
        abs(sum(signs)) for signs in itertools.product((-1, 1), repeat=len(discordant))
    ]
    result["win_rate_exact_paired_test"] = {
        "discordant_pairs": len(discordant),
        "two_sided_p": float(np.mean(np.asarray(null) >= abs(sum(discordant)))),
        "method": "Exact two-sided paired sign test on discordant wins (McNemar conditional test).",
    }
    return result


def audit(games):
    counts = Counter()
    errors = Counter()
    bad_examples = []
    for g in games:
        counts["games"] += 1
        counts["early_guess_games"] += g["early_guess"]
        counts["early_guess_wins"] += g["early_guess"] and g["won"]
        if g["early_guess"]:
            resolved = sum(p > 0 for p in g["turns"][-1]["posterior_before"]) == 1
            counts["early_after_singleton"] += resolved
            counts["early_with_multiple_remaining"] += not resolved
        counts["zero_question_guesses"] += g["questions"] == 0
        assert (
            abs(
                g["reward"]
                - (float(g["won"]) - 0.03 * g["questions"] - 0.1 * g["invalid_count"])
            )
            < 1e-10
        )
        singleton_streak = 0
        for t in g["turns"]:
            counts["post_budget_non_guesses"] += bool(t.get("forced_end"))
            counts["post_budget_asks"] += bool(t.get("forced_end")) and t[
                "action"
            ].startswith("ASK: ")
            counts["counted_questions"] += t["is_question"]
            counts["invalid_questions"] += t["invalid"] and t["is_question"]
            if t["invalid"]:
                errors[t.get("error", "unknown")] += 1
                continue
            if not t["is_question"]:
                continue
            counts["valid_questions"] += 1
            counts["item_equality_questions"] += t["enumeration"]
            counts["single_named_item_questions"] += t["named_items"] == 1
            counts["name_list_questions"] += t["named_items"] >= 2
            counts["large_name_lists_original_N"] += t["named_items"] >= g["n"] / 4
            counts["valid_zero_eig_questions"] += t["eig"] < 1e-12
            counts["repeated_splits"] += t["reask"]
            counts["exact_one_bit_questions"] += t["eig"] >= 1 - 1e-12
            counts["at_least_0_9_bit_questions"] += t["eig"] >= 0.9
            expression = parse(t["action"][5:])
            if not t["enumeration"]:
                if expression.kind == "attribute":
                    counts["single_attribute_questions"] += 1
                elif (
                    expression.kind == "not"
                    and expression.children[0].kind == "attribute"
                ):
                    counts["negated_single_attribute_questions"] += 1
                else:
                    counts["compound_attribute_questions"] += 1
            support = sum(p > 0 for p in t["posterior_before"])
            counts["lists_at_least_half_remaining"] += (
                t["named_items"] >= 2 and t["named_items"] >= support / 2
            )
            singleton_streak = singleton_streak + 1 if t["named_items"] == 1 else 0
            counts["consecutive_single_item_transitions"] += singleton_streak >= 2
            if t["named_items"] >= 2 and len(bad_examples) < 2:
                bad_examples.append(
                    {
                        "game_id": g["game_id"],
                        "update": g["update"],
                        "member": g.get("member"),
                        "action": t["action"],
                    }
                )
    return {
        "counts": dict(counts),
        "invalid_causes": dict(errors),
        "name_list_examples": bad_examples,
        "parser_exploit_assessment": "Every accepted predicate is replayed through the fixed safe AST parser and exact table evaluation. Invalid/malicious strings never execute code. No broader adversarial security guarantee is inferred.",
        "no_rules_changed": True,
    }


def stopping_confidence(games, records):
    total = expected_reward = 0
    ambiguous = ambiguous_wins = 0
    for g in games:
        t = g["turns"][-1]
        names = records[g["game_id"]]["world"]["names"]
        probability = 0
        if t["action"].startswith("GUESS: ") and t["action"][7:].strip() in names:
            probability = t["posterior_before"][names.index(t["action"][7:].strip())]
            unresolved = sum(p > 0 for p in t["posterior_before"]) > 1
            ambiguous += unresolved
            ambiguous_wins += unresolved and g["won"]
        total += probability
        expected_reward += (
            probability - 0.03 * g["questions"] - 0.1 * g["invalid_count"]
        )
    return {
        "games": len(games),
        "guesses_with_multiple_remaining": ambiguous,
        "wins_with_multiple_remaining": ambiguous_wins,
        "mean_posterior_win_probability_at_stopping": total / len(games),
        "mean_reward_using_posterior_win_probability": expected_reward / len(games),
        "interpretation": "Post-hoc stopping audit, not a new primary score or reward. Assign zero to no-guess endings and use the posterior mass of the chosen item otherwise. This separates logged guess confidence from lucky realized wins.",
    }


def main():
    out = ROOT / "results/pilot_A"
    config = json.loads((ROOT / "experiments/pilot_A.json").read_text())
    manifest = json.loads((ROOT / "experiments/pilot_A_games.json").read_text())
    completion = json.loads((out / "completion.json").read_text())
    directory = ROOT / "runs" / config["run_id"]
    paths = sorted((directory / "games").glob("*.json"))
    games = (
        [json.loads(p.read_text()) for p in paths]
        if paths
        else [json.loads(line) for line in gzip.open(out / "games.jsonl.gz", "rt")]
    )
    games.sort(
        key=lambda g: (g["kind"], g["update"], g["game_id"], g.get("member") or 0)
    )
    req_paths = sorted((directory / "requests").glob("*.json"))
    requests = (
        [json.loads(p.read_text()) for p in req_paths]
        if req_paths
        else [json.loads(line) for line in gzip.open(out / "requests.jsonl.gz", "rt")]
    )
    if not req_paths:
        responses = {
            r["entry_id"]: r["response"]
            for line in gzip.open(out / "responses.jsonl.gz", "rt")
            if (r := json.loads(line))
        }
        for r in requests:
            r["response"] = responses[r["entry_id"]]
    by_entry = {r["entry_id"]: r for r in requests}
    records = {r["record"]["id"]: r["record"] for r in manifest["training"]}
    records.update({r["id"]: r for r in manifest["development"]})
    rendering = Rendering(config["primary_model"], config)
    used = set()
    for g in games:
        record = records[g["game_id"]]
        replay = Game(record, grammar_version=config["grammar_version"])
        expected_step = g["update"] - 1 if g["kind"] == "train" else g["update"]
        assert g["policy_step"] == expected_step
        assert len(g["turns"]) == len(g["trajectory"])
        for index, (turn, tape) in enumerate(zip(g["turns"], g["trajectory"])):
            ids = rendering.prompt(candidate_messages(record, replay.turns)).to_ints()
            assert tape["ob"] == ids
            usage = turn["usage"]
            request = by_entry[usage["entry_id"]]
            assert request["settled"] and request["request_id_saved_before_dispatch"]
            assert (
                request["request_id"]
                == request["receipt"]["request_id"]
                == usage["request_id"]
            )
            assert (
                request["request_id"].rsplit(":", 1)[0]
                == completion["snapshots"][str(expected_step)]["id"]
            )
            assert (
                request["key"]
                == g["scope"]
                + config["primary_model"]
                + "/"
                + g["game_id"]
                + f"/turn-{index}"
            )
            params = request["parameters"]
            assert params["seed"] == seed_for(
                g["sampling_seed_namespace"], g["game_id"], index
            ) % (2**31)
            assert (
                params["max_tokens"] == 2048
                and params["temperature"] == 0.7
                and params["top_p"] == 1
                and params["top_k"] == -1
            )
            payload = {
                "model": config["primary_model"],
                "prompt_ids": ids,
                "sampling_params": params,
            }
            assert (
                hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
                == request["signature"]
            )
            sequence = request["response"]["sequences"][0]
            assert (
                sequence["tokens"] == tape["tokens"]
                and sequence["logprobs"] == tape["logprobs"]
            )
            assert rendering.decode(sequence["tokens"])["action"] == turn["raw_action"]
            before = replay.reward
            reproduced = replay.step(
                turn["raw_action"],
                reasoning_tokens=turn["reasoning_tokens"],
                action_tokens=turn["action_tokens"],
                predicate_tokens=turn["predicate_tokens"],
                truncated=turn["truncated"],
            )
            for field in ("answer", "invalid", "enumeration", "is_question", "reask"):
                assert reproduced[field] == turn[field]
            assert abs(reproduced["eig"] - turn["eig"]) < 1e-12
            np.testing.assert_allclose(
                reproduced["posterior_after"],
                turn["posterior_after"],
                atol=1e-12,
                rtol=0,
            )
            assert abs(replay.reward - before - tape["reward"]) < 1e-12
            assert usage["actual_usd"] == sample_cost(
                config["primary_model"],
                len(ids),
                len(sequence["tokens"]),
                request["prompt_cache_hit_tokens"],
            )
            used.add(usage["entry_id"])
        assert (
            replay.done
            and replay.won == g["won"]
            and abs(replay.reward - g["reward"]) < 1e-10
        )
    assert used == set(by_entry)
    op_paths = sorted((directory / "operations").glob("*.json"))
    operations = (
        [json.loads(p.read_text()) for p in op_paths]
        if op_paths
        else [json.loads(line) for line in gzip.open(out / "operations.jsonl.gz", "rt")]
    )
    ops = {o["key"]: o for o in operations}
    curve = json.loads((out / "learning_curve.json").read_text())["updates"]
    for step in range(1, completion["updates"] + 1):
        gs = sorted(
            [g for g in games if g["kind"] == "train" and g["update"] == step],
            key=lambda g: g["member"],
        )
        assert len(gs) == 8 and len({g["game_id"] for g in gs}) == 1
        data, archive, returns, advantages = group_data(
            [unpack_trajectory(g["trajectory"]) for g in gs]
        )
        assert archive == json.loads(
            gzip.decompress((out / f"training-data-{step:02d}.json.gz").read_bytes())
        )
        op = ops[f"forward-{step:02d}"]
        assert op["payload"]["loss_fn"] == "importance_sampling"
        assert (
            op["payload"]["data_sha256"]
            == hashlib.sha256(json.dumps(archive, sort_keys=True).encode()).hexdigest()
        )
        tokens = sum(d.model_input.length for d in data)
        assert tokens == op["payload"]["tokens"] == curve[step - 1]["training_tokens"]
        np.testing.assert_allclose(
            returns, curve[step - 1]["returns"], atol=1e-12, rtol=0
        )
        np.testing.assert_allclose(
            advantages, curve[step - 1]["advantages"], atol=1e-12, rtol=0
        )
        assert curve[step - 1]["gradient_usd"] == op["actual_usd"]
        sampled = [
            np.asarray(row["loss_fn_inputs"]["logprobs"]["data"])[
                np.asarray(row["training_mask"], dtype=bool)
            ]
            for row in archive
        ]
        trained = (
            [
                np.asarray(output["logprobs"]["data"])[
                    np.asarray(row["training_mask"], dtype=bool)
                ]
                for output, row in zip(op["response"]["loss_fn_outputs"], archive)
            ]
            if "response" in op
            else [np.asarray(values) for values in op["action_logprobs"]]
        )
        assert len(trained) == len(sampled)
        differences = np.concatenate([t - p for t, p in zip(trained, sampled)])
        assert (
            abs(
                np.mean(differences)
                - curve[step - 1]["mean_train_minus_sample_logprob"]
            )
            < 1e-10
        )
        assert (
            abs(
                np.max(np.abs(differences))
                - curve[step - 1]["max_abs_train_minus_sample_logprob"]
            )
            < 1e-10
        )
        expected = (
            Decimal(tokens) * rates(config["primary_model"])["train"] / 1_000_000
        ).quantize(Decimal(".000001"), rounding="ROUND_CEILING")
        assert Decimal(op["actual_usd"]) == expected
    training = [g for g in games if g["kind"] == "train"]
    dev = {
        step: sorted(
            [g for g in games if g["kind"] == "dev" and g["update"] == step],
            key=lambda g: g["game_id"],
        )
        for step in config["development_checks"]
        if step <= completion["updates"]
    }
    assert (
        len(training) == completion["training_games"]
        and sum(map(len, dev.values())) == completion["development_games"]
    )
    status = Ledger(ROOT / "ledger.json").status()
    entries = [
        e for e in status["entries"] if e["operation"].startswith("[pilot-A-v1] ")
    ]
    spent = sum(
        (Decimal(e["actual_usd"]) for e in entries if e["state"] == "settled"),
        Decimal(0),
    )
    held = sum(
        (Decimal(e["reserved_usd"]) for e in entries if e["state"] in ACTIVE_STATES),
        Decimal(0),
    )
    assert spent + held <= Decimal("2")
    result = {
        "complete": True,
        "initial_policy": "raw_base_no_sft",
        "updates": curve,
        "development": {
            str(k): {"point": game_metrics(gs), "ci95": summarize(gs, bootstrap=10000)}
            for k, gs in dev.items()
        },
        "paired_development_final_minus_base": paired_change(dev[0], dev[max(dev)]),
        "training_audit": audit(training),
        "development_audit": audit([g for gs in dev.values() for g in gs]),
        "base_development_audit": audit(dev[0]),
        "final_development_audit": audit(dev[max(dev)]),
        "guess_consistency_audit": {
            "training": consistency_audit(training, records),
            "base_dev": consistency_audit(dev[0], records),
            "final_dev": consistency_audit(dev[max(dev)], records),
        },
        "stopping_confidence_audit": {
            "training": stopping_confidence(training, records),
            "base_dev": stopping_confidence(dev[0], records),
            "final_dev": stopping_confidence(dev[max(dev)], records),
        },
        "group_signal_audit": {
            "nonconstant_return_groups": sum(
                r["reward_variance"] > 1e-12 for r in curve
            ),
            "groups": len(curve),
            "groups_with_win_variance": sum(r["win_variance"] > 1e-12 for r in curve),
            "zero_win_groups": [r["update"] for r in curve if r["wins"] == 0],
            "zero_win_groups_with_cost_only_variance": [
                r["update"]
                for r in curve
                if r["wins"] == 0 and r["reward_variance"] > 1e-12
            ],
        },
        "per_update_interpretation": "Training outcomes are on the policy before each update. Eight games within an update share one hidden target and table. Curriculum changes at updates 5 and 13, so the fixed development cases, not raw training slopes alone, assess learning.",
        "uncertainty": "One pilot seed and eight fixed noiseless development cases. Paired bootstrap resamples complete games within N; no between-seed uncertainty is estimated. No frozen, noisy or transfer model evaluation ran.",
        "sample_train_logprob_diagnostic": {
            "mean_difference_range_nats": [
                min(r["mean_train_minus_sample_logprob"] for r in curve),
                max(r["mean_train_minus_sample_logprob"] for r in curve),
            ],
            "maximum_absolute_token_difference_nats": max(
                r["max_abs_train_minus_sample_logprob"] for r in curve
            ),
            "interpretation": "Native token sequences match exactly; training and sampling log probabilities are not bit-identical. The backend cause is not established. The standard importance-sampling loss uses the recorded rollout log probabilities; no correction or experiment setting changed.",
        },
        "cost": {
            "pilot_spent_usd": str(spent),
            "pilot_held_usd": str(held),
            "cap_including_holds_usd": "2.000000",
            "project": {k: status[k] for k in status if k != "entries"},
        },
        "verification": {
            "sampled_games": len(games),
            "sampling_request_signatures_and_predispatch_ids": len(used),
            "gradient_batches_verified": completion["updates"],
            "outcome_rewards_only": True,
            "prompt_loss_tokens": 0,
            "frozen_games_in_gradients": 0,
        },
    }
    save_json(out / "summary.json", result)
    write_gzip(out / "games.jsonl.gz", games)
    write_gzip(
        out / "requests.jsonl.gz",
        [
            {k: v for k, v in r.items() if k != "response"}
            for r in sorted(requests, key=lambda x: x["key"])
        ],
    )
    write_gzip(
        out / "responses.jsonl.gz",
        [
            {"entry_id": r["entry_id"], "response": r["response"]}
            for r in sorted(requests, key=lambda x: x["entry_id"])
        ],
    )
    compact = []
    for op in operations:
        row = {k: v for k, v in op.items() if k != "response"}
        if op["key"].startswith("forward-"):
            if "response" in op:
                step = int(op["key"].split("-")[1])
                archive = json.loads(
                    gzip.decompress(
                        (out / f"training-data-{step:02d}.json.gz").read_bytes()
                    )
                )
                row["response_sha256"] = hashlib.sha256(
                    json.dumps(op["response"], sort_keys=True).encode()
                ).hexdigest()
                row["reported_metrics"] = op["response"].get("metrics", {})
                row["action_logprobs"] = [
                    np.asarray(o["logprobs"]["data"])[
                        np.asarray(d["training_mask"], dtype=bool)
                    ].tolist()
                    for o, d in zip(op["response"]["loss_fn_outputs"], archive)
                ]
        else:
            row["response"] = op["response"]
        compact.append(row)
    write_gzip(out / "operations.jsonl.gz", sorted(compact, key=lambda o: o["key"]))
    pairs = []
    for identity in manifest["examples"]:
        pairs.append(
            {
                "game_id": identity,
                "record": records[identity],
                "base": next(g for g in dev[0] if g["game_id"] == identity),
                "final": next(g for g in dev[max(dev)] if g["game_id"] == identity),
                "selection": "Preselected before training; final scheduled development snapshot.",
            }
        )
    write_gzip(out / "example_games.jsonl.gz", pairs)
    print(
        json.dumps(
            {
                "cost": result["cost"],
                "development": {
                    k: v["point"] for k, v in result["development"].items()
                },
                "paired_change": result["paired_development_final_minus_base"],
                "verification": result["verification"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
