"""Write the pilot gate, including every update and the priced main choices."""

import json
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.worlds import ROOT


def number(value, places=3):
    return "—" if value is None else f"{value:.{places}f}"


def percent(value):
    return "—" if value is None else f"{100 * value:.1f}%"


def usd(value):
    return "$" + str(
        Decimal(str(value)).quantize(Decimal(".01"), rounding=ROUND_CEILING)
    )


def headroom(value):
    return "$" + str(Decimal(str(value)).quantize(Decimal(".01"), rounding=ROUND_FLOOR))


def main():
    folder = ROOT / "results/pilot_A"
    s = json.loads((folder / "summary.json").read_text())
    completion = json.loads((folder / "completion.json").read_text())
    plans = json.loads((ROOT / "research/main_options_after_pilot.json").read_text())
    last = str(completion["updates"])
    base = s["development"]["0"]["point"]
    final = s["development"][last]["point"]
    delta = s["paired_development_final_minus_base"]
    ig = delta["eig_per_question"]
    train = s["training_audit"]["counts"]
    stop = s["stopping_confidence_audit"]
    signal = s["group_signal_audit"]
    project = s["cost"]["project"]
    lines = [
        "# Raw-base RL pilot gate",
        "",
        f"Completed 2026-11-18: **{completion['updates']} A updates, {completion['training_games']} training games and {completion['development_games']} development games**. Raw Qwen3-8B with candidate feedback improved from {base['wins']}/8 to {final['wins']}/8 on the fixed development cases; EIG/question rose from {base['eig_per_question']:.3f} to {final['eig_per_question']:.3f}. The EIG change is {ig['final_minus_base']:+.3f} bits/question, paired 95% CI [{ig['ci95'][0]:+.3f}, {ig['ci95'][1]:+.3f}]. This is encouraging and inconclusive, not evidence of optimal search. Main runs have not started.",
        "",
        "![Pilot learning curves](results/pilot_A/charts/pilot-learning.png)",
        "",
        "## What trained",
        "",
        "The policy began at raw Qwen3-8B, with no SFT adapter or optimizer state loaded. Random-question SFT is removed from the main plan because it lowered pooled EIG by 0.1444 bits/question in the paired candidate-set qualification. Its historical data, charges and storage holds remain intact. Its toy-table exposure does not enter the main RL policy.",
        "",
        "Rank-32 LoRA, seed 11, attention/MLP/output projections trainable; Adam learning rate 4e-5, beta1=0.9, beta2=0.95, epsilon=1e-8, zero weight decay and no gradient clipping. These optimizer defaults match the pinned cookbook RL-loop recipe. One importance-sampling forward/backward and optimizer step per eight-game group; no extra substeps, KL penalty, SFT loss or information reward. Total returns are centered within the group and divided by population standard deviation plus 1e-8; numerically constant returns get zero advantages. Zero-advantage batches remain in the fixed schedule; Adam may still carry momentum from previous gradients.",
        "",
        "The reward stayed +1 for a win, -0.03 per question and -0.1 per INVALID question. Every group shares one animal table, subset and hidden target, with eight distinct requested generation seeds. The curriculum stayed 4 updates at N=4, 8 at N=8 and 4 at N=16. All worlds come from the fixed 200-row training pool through training_game. The eight separate development games never enter gradients. No noisy, transfer or frozen-test model evaluation ran.",
        "",
        "The main observation remained candidate-set-v1 with exact attribute-code aliases, a stable full table prefix and lists after answers. Caps stayed at 2,048 generated tokens per turn and 32K context, with thinking disabled. EIG is measurement only. Only generated action tokens, including termination tokens, receive direct loss; context still influences their predictions. Cookbook rollout, renderer and training-data helpers are reused through the ledger guard. [Frozen configuration](experiments/pilot_A.json), [games and example selection](experiments/pilot_A_games.json), [preflight](research/pilot_A_preflight.json).",
        "",
        "## Every training update",
        "",
        "Each row describes eight on-policy games sampled **before** that update. The table and target change between groups; changes across rows are not a paired learning estimate. Invalid and enumeration rates use all counted questions, including losses. Lists means at least two distinct item equalities. G nonzero is the per-update group share followed by the cumulative share. Undefined win-conditioned values remain undefined.",
        "",
        "| Update | N | Mean reward | Wins/8 | EIG/Q | Q/win | Item == % | Lists % | Invalid % | G nonzero / cumulative | Output tokens/game |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for r in s["updates"]:
        lines.append(
            f"| {r['update']} | {r['n']} | {r['mean_reward']:.3f} | {r['wins']}/8 | {number(r['eig_per_question'])} | {number(r['questions_per_win'], 2)} | {percent(r['enumeration_rate'])} | {percent(r['name_list_rate'])} | {percent(r['invalid_question_rate'])} | {percent(r['nonzero_group_fraction'])} / {percent(r['cumulative_nonzero_group_fraction'])} | {r['output_tokens_per_game']:.2f} |"
        )
    lines.extend(
        [
            "",
            f"The four-update stop rule passed: **3/4 groups (75%)** had nonzero return variance, above 25%. Over the whole pilot, **{signal['nonconstant_return_groups']}/16** groups had return variance and **{signal['groups_with_win_variance']}/16** had win variance. Updates {', '.join(map(str, signal['zero_win_groups_with_cost_only_variance']))} had no wins but nonzero cost-driven return variance. The stop test alone does not prove useful win signal. No extra stop rule was added.",
            "",
            "## Fixed development curve",
            "",
            "These are the same four N=4 and four N=8 training-pool development cases at each checkpoint, with paired generation seeds. They are not held-out items or the frozen evaluation bank. Development CIs resample complete games. The eight rollouts in each training row share a table and target; one group cannot estimate variation across start states. There is one pilot seed, so no between-seed uncertainty estimate.",
            "",
            "| Policy update | Mean reward | Wins/8 | EIG/Q [95% bootstrap CI] | Q/win | Output tokens/game |",
            "| ---: | ---: | ---: | --- | ---: | ---: |",
        ]
    )
    for step, d in s["development"].items():
        p = d["point"]
        ci = d["ci95"]["eig_per_question_ci95"]
        lines.append(
            f"| {step} | {p['mean_reward']:.3f} | {p['wins']}/8 | {p['eig_per_question']:.3f} [{ci[0]:.3f}, {ci[1]:.3f}] | {number(p['questions_per_win'], 2)} | {p['output_tokens_per_game']:.2f} |"
        )
    lines.extend(
        [
            "",
            f"Most observed development improvement appeared between updates 4 and 8. EIG then stayed near 0.65 and ended at {final['eig_per_question']:.3f}; the scheduled final checkpoint is reported, not the highest intermediate score. Paired EIG permutation p={delta['eig_per_game_exact_paired_permutation']['two_sided_p']:.3f}; exact paired win-test p={delta['win_rate_exact_paired_test']['two_sided_p']:.3f}. The win bootstrap change interval is [{delta['win_rate']['ci95'][0] * 100:.1f}, {delta['win_rate']['ci95'][1] * 100:.1f}] percentage points, but with only three discordant pairs the exact test remains weak. The small-case bootstrap interval should not be treated as conclusive evidence. No main-study claim rests on these eight cases.",
            "",
            "## Strategy and reward-hacking audit",
            "",
            f"**No item-name enumeration occurred:** 0/{train['counted_questions']} training questions and 0/23 final-development questions. There was no item-by-item search, multi-item name list, giant half-list, or consecutive singleton-item enumeration. These actions remained legal. Accepted training questions were {train['single_attribute_questions']} single attributes, {train['negated_single_attribute_questions']} negated single attributes and {train['compound_attribute_questions']} Boolean attribute predicates. This is attribute-based play, not proof of balanced bisection.",
            "",
            f"There were {train['valid_zero_eig_questions']} valid zero-EIG training questions and {train['repeated_splits']} repeated splits. On the paired development cases, zero-EIG questions fell from **13/29 to 7/23**, repeated splits from **8 to 5**, and exactly-one-bit questions rose from **3 to 4**. The main observed efficiency gain was removing wasted questions. The final model remains far below the one-bit ceiling and matched greedy reference.",
            "",
            f"**Risky stopping remains material.** Training had {train['early_guess_games']}/128 early-guess games ({train['early_guess_wins']} wins), and no zero-question guess. Early means fewer questions than ceil(log2 N): {train['early_after_singleton']} of these already had singleton support after an uneven split, while {train['early_with_multiple_remaining']} still had multiple possibilities. In the final development check, **{stop['final_dev']['guesses_with_multiple_remaining']}/8 guesses** occurred with multiple candidates remaining and **{stop['final_dev']['wins_with_multiple_remaining']} of 7 wins** came from those guesses. Only three final wins followed singleton. Neither training nor final development guessed an eliminated candidate or guessed wrongly at singleton; every one of the 45 singleton-reaching training games won.",
            "",
            f"A post-hoc stopping audit replaces realized win with the posterior probability of the chosen item, assigning zero to a no-guess ending. Mean logged guess confidence rose from **{stop['base_dev']['mean_posterior_win_probability_at_stopping']:.3f} to {stop['final_dev']['mean_posterior_win_probability_at_stopping']:.3f}**, while realized win rate rose from 0.500 to 0.875. Part of the win gain was luck. This audit does not change any reward or primary score. Win-conditioned questions alone would overstate progress.",
            "",
            f"There were **{train['invalid_questions']}/{train['counted_questions']} INVALID training questions** ({100 * train['invalid_questions'] / train['counted_questions']:.2f}%), all in updates 1–4, and none in the development checks. Causes: two excessive-nesting expressions, one trailing-token expression, six unknown `long_ears` attributes and six missing closing parentheses. Two extra ASK actions after budget exhaustion ended games as losses; they did not increase the question counter or win. There were no truncated sampled turns or visible reasoning tokens. Zero visible reasoning follows the disabled-thinking protocol and does not measure internal computation.",
            "",
            "All accepted predicates were replayed through the safe AST parser against exact table rows; answers, posterior updates, EIG and rewards matched. The malformed outputs were rejected, with no parsing exploit observed. No rule, grammar limit, output cap or legal enumeration form was changed. [Full machine-readable audit](results/pilot_A/summary.json).",
            "",
            "![Pilot behavior audit](results/pilot_A/charts/pilot-behavior.png)",
            "",
            "## Two paired games",
            "",
            "[EXAMPLE_GAMES.md](results/pilot_A/EXAMPLE_GAMES.md) shows the two preselected development targets side by side, raw base at update 0 and the final model at update 16, with every action, answer, remaining-count and the shared public table. These are games from the final scheduled development snapshot, not cherry-picked training wins. They use existing development calls, so no extra sample was purchased. [Complete paired records](results/pilot_A/example_games.jsonl.gz).",
            "",
            "## Cost, collection and implementation incident",
            "",
            f"Recorded pilot token usage was **${s['cost']['pilot_spent_usd']}**, plus **${s['cost']['pilot_held_usd']}** held for four native checkpoints and one external export: **$0.541204 including holds**, below the approved **$2.00** ceiling. The forecast was $0.742968 for sampling/gradients plus $0.30 checkpoint holds, or $1.564452 with 1.5x margin. Fewer turns, shrinking new lists and observed sampling caches lowered recorded costs; gradient usage was priced for full input tokens despite masked prompt loss. No question-cap reduction or incomplete game exclusion produced the saving.",
            "",
            f"Project usage is **${project['spent_usd']}**, total holds **${project['held_usd']}**, and **${project['available_usd']} remains** under $50. The nine excluded old attempts still hold $0.012813; the earlier SFT storage holds remain $0.10. New pilot checkpoint holds add $0.25. Storage is unknown until billing reconciliation; completed futures are already collected. Usage charges use observed/submitted tokens and the [provider rate card](https://tinker-docs.thinkingmachines.ai/tinker/models.json), rechecked on 2026-11-18, rather than final invoices. The final adapter is downloaded under the ignored runs/pilot-A-v1/adapter directory with hashes.",
            "",
            "An initial gradient reservation failed locally because the specialized SDK forward_backward method does not accept a per-call max_retries keyword. The local Python argument binder rejected it before creating an HTTP coroutine. That reservation was proven unsubmitted and reconciled at $0; its journal and original preflight are preserved. Both forward_backward and optim_step now rely on the SDK client’s existing max_retries=0 setting, and a regression test invokes the actual production update through native SDK resources. The 16 already sampled games were reused. No reward, prompt, seed, cap, data or evaluation setting changed. [Incident and proof](research/pilot_A_local_adapter_incident.json), [implementation amendment](research/pilot_A_preflight.json).",
            "",
            "Network interruptions were recovered by pausing producers, draining active HTTP operations, reconnecting, and collecting saved sampling and training futures concurrently before new submissions. A retrieve_future 408 always kept its original request ID and hold. No accepted gradient or optimizer work was resubmitted. Sampling and mutation IDs were saved before dispatch and checked against receipts or recovered results. No new response-expiry replacement was needed.",
            "",
            f"Training and sampling log probabilities were not bit-identical despite matching native token sequences: per-update mean signed differences ranged from {s['sample_train_logprob_diagnostic']['mean_difference_range_nats'][0]:.4f} to {s['sample_train_logprob_diagnostic']['mean_difference_range_nats'][1]:.4f} nats, with a maximum absolute token difference of {s['sample_train_logprob_diagnostic']['maximum_absolute_token_difference_nats']:.3f}. The backend cause is unverified. The standard importance-sampling loss used recorded rollout log probabilities throughout; no correction was introduced mid-run. These diagnostics are saved per update.",
            "",
            "## Main-run choices — not authorized",
            "",
            "Both choices initialize every seed from raw Qwen3-8B, not SFT or the pilot adapter. A uses p=0; B uses p=0.10. Groups stay at eight and the reward, aliases, candidate feedback and 2,048 cap remain unchanged. The curricula below are new proposals, to be frozen only after the user chooses. Each seed keeps one scheduled endpoint, evaluated on all 280 frozen games (28 per cell). A new raw-base candidate-feedback control is evaluated once on the same bank. Intermediate development samplers are ephemeral; no extra retained checkpoints are selected by test scores.",
            "",
            "| Choice | A / B seeds | Updates/seed | Training games/seed | Total training games | Forecast incl. 1.5x margin and checkpoint holds | Remaining after forecast |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name, o in plans["options"].items():
        lines.append(
            f"| {name} | {len(o['seeds_A'])} / {len(o['seeds_B'])} | {o['updates_per_seed']} | {o['training_games_per_seed']} | {o['total_training_games']} | {usd(o['total_with_1_5_margin_usd'])} | {headroom(o['remaining_after_margin_usd'])} |"
        )
    lines.extend(
        [
            "",
            "| Choice | N=4 | N=8 | N=16 | N=32 | N=64 | N=128 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name, o in plans["options"].items():
        lines.append(
            "| "
            + name
            + " | "
            + " | ".join(str(r["updates"]) for r in o["curriculum"])
            + " |"
        )
    lines.extend(
        [
            "",
            "| Choice | Training | Development | Raw + endpoint frozen evals | Hard mode, 40 games | Checkpoint holds | Total before margin |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name, o in plans["options"].items():
        lines.append(
            f"| {name} | ${o['training_usd']:.2f} | ${o['development_usd']:.2f} | ${o['full_evaluation_usd']:.2f} | ${o['hard_mode_40_games_usd']:.2f} | ${o['checkpoint_holds_usd']:.2f} | ${o['total_before_margin_usd']:.2f} |"
        )
    lines.extend(
        [
            "",
            "Per-seed training forecasts (sampling plus gradients, with 1.5x margin; evaluation and checkpoint holds are in the totals above): "
            + "; ".join(
                f"{name}: {usd(o['training_usd_per_A_seed'] * 1.5)} per A seed and {usd(o['training_usd_per_B_seed'] * 1.5)} per B seed"
                for name, o in plans["options"].items()
            )
            + ". Quoted total forecasts round upward and remaining funds downward to cents.",
            "",
            "S uses A seeds 11, 23, 37 and B seeds 41, 53; U uses A seeds 11, 23 and B seed 41. Each seed uses the same eight development games every four updates and at its scheduled endpoint; the existing raw development control is reused. This buys a visible curve without retaining extra checkpoints. The N=4/8 development curve is descriptive; larger-size, noisy and transfer comparisons use the frozen endpoints. Both include the end-of-project hard-mode slice: raw base and predetermined final A seed 11, 20 games each, with no hard-mode training. Tools, foods and the retired large reference have no paid allocation.",
            "",
            "**Recommend U as an exploratory continuation.** It buys more training start states and more updates at N=16/32, where the pilot still has room to learn before the untested larger sizes. The observed small-game gain appeared by update 8 but then plateaued, below one bit; more updates are not guaranteed to help. S provides more seed replication but a short learning horizon. U has only one B seed, so it cannot estimate between-seed variability of noisy training; that limitation must accompany any noise claim. Risky stopping remains an issue under the unchanged reward.",
            "",
            "Forecasts use native token counts on random and greedy-predicate reference trajectories, calibrated upward if they underpredict measured pilot uncached sampling plus gradients. Output proxies are max(mean,p90) observed pilot lengths. Training receives no cache credit. Stable-weight evaluation receives 60% cache credit, below the minimum 75.4% observed on the trained development snapshots; both the forecast times 1.5 and a separate zero-cache reference total must fit remaining funds. Hard mode is priced with full 2,048-token outputs until context stop, rather than the short provided-state proxy. The zero-cache reference totals, before another margin, are $"
            + f"{plans['options']['S']['zero_cache_total_without_extra_margin_usd']:.2f} (S) and ${plans['options']['U']['zero_cache_total_without_extra_margin_usd']:.2f} (U).",
            "",
            "No large-N or noisy model pilot was run. Legal name-list strategies and format failures could increase output/context costs. These are forecasts, not bills or guarantees of completion. The ledger refuses any call whose reservation would exceed $50; it will not silently reduce caps, cells or updates. The 50% margin is already included above. [Reproducible profiles, per-seed costs and assumptions](research/main_options_after_pilot.json).",
            "",
            "## Verification and next decision",
            "",
            f"120 unit tests pass. Offline replay verified all **{s['verification']['sampled_games']} games and {s['verification']['sampling_request_signatures_and_predispatch_ids']} sampling calls**, every group’s return/advantage arrays and all 16 gradient batches. Frozen game files, old prompt hashes, prior ledger entries and cap approval remain intact. [Final validation](results/pilot_A/validation.json), [archive-only reproduction](results/pilot_A/reproduction.json).",
            "",
            "Reproduce at this gate commit with `python3 scripts/analyze_rl_pilot.py`, `python3 scripts/verify_rl_pilot.py`, `python3 scripts/plot_rl_pilot.py`, `python3 scripts/price_main_runs.py`, and `python3 scripts/write_pilot_gate.py`. These use saved responses and perform no Tinker operations. Native and external checkpoint TTLs are two hours; the downloaded adapter persists locally.",
            "",
            "**Pilot complete. Stop for the user to choose S, U, or a revised experiment. No main run is authorized or started.**",
            "",
        ]
    )
    (ROOT / "PILOT_GATE.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
