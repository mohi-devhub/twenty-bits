"""Write the A seed 11 gate from saved measurements and a factual assessment."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.worlds import ROOT


def num(value, digits=3):
    return "—" if value is None else f"{value:.{digits}f}"


def percent(value):
    return "—" if value is None else num(100 * value, 1)


def interval(point, ci):
    return num(point) + (f" [{num(ci[0])}, {num(ci[1])}]" if ci else "")


def bins(row):
    return [
        f"{row['bins'][k]['wins']}/{row['bins'][k]['guesses']}"
        for k in ("1", "2", "3", "4+")
    ]


def main():
    folder = ROOT / "results/main_A11"
    s = json.loads((folder / "summary.json").read_text())
    proof = json.loads((ROOT / "research/main_A11_preflight.json").read_text())
    base = s["development"]["0"]["point"]
    final = s["development"]["30"]["point"]
    delta = s["paired_development_final_minus_base"]
    frozen = s["frozen_evaluation"]
    assessment = json.loads((ROOT / "research/main_A11_assessment.json").read_text())
    p = s["cost"]["project"]
    train = s["training_audit"]["counts"]
    lines = [
        "# Main A seed 11 gate",
        "",
        "Completed the scheduled **30 updates and 240 training games**, with **64 new development games**, **280 new matched raw-base frozen games** and **280 endpoint frozen games**. Eight raw development games are reused from the matched pre-RL control. A seed 23, B seed 41 and hard-mode evaluation have not started. Work stops at this gate.",
        "",
        *assessment["learning_assessment"],
        "",
        "![Main learning curve](results/main_A11/charts/main-learning.png)",
        "",
        "## Fixed setup and curriculum",
        "",
        "Raw Qwen3-8B, no SFT or pilot adapter loaded; rank-32 LoRA seed 11, learning rate 4e-5 and unchanged cookbook Adam parameters. One eight-game group per update, with one table and target shared by its independently seeded rollouts. Group returns are standardized with population standard deviation; constant returns give zero advantage. Loss is the cookbook importance-sampling objective on generated tokens only. Reward remains +1 win, -0.03/question and -0.1/INVALID. EIG is measured, never rewarded.",
        "",
        "| N | Updates | Training games |",
        "| ---: | --- | ---: |",
    ]
    for r in proof["curriculum"]:
        lines.append(
            f"| {r['n']} | {r['update_start']}–{r['update_end']} | {8 * (r['update_end'] - r['update_start'] + 1)} |"
        )
    lines += [
        "",
        "**The curriculum reaches N=32 and N=128**, matching the frozen animal cells. N=256 remains size transfer on relabeled synthetic. Every gradient uses only the fixed 200-row animal training pool; development, held-out profiles and frozen games never enter gradients.",
        "",
        "Prompt candidate-set-v1, exact attribute aliases, 2,048 output tokens with thinking disabled, 32K context and original-N question budgets stayed fixed. The provided state means the main question is question selection, rather than maintaining state from history. Checkpoints were not selected on frozen scores: only the scheduled update-30 endpoint was retained and evaluated. [Frozen config](experiments/main_A11.json), [cases](experiments/main_A11_games.json), [preflight](research/main_A11_preflight.json).",
        "",
        "## All 30 training updates",
        "",
        "Rows contain eight games sampled before that optimizer update. Each group has a different start state, so the raw training curve mixes learning, difficulty and curriculum. The fixed development curve below supplies a paired comparison. Q/win is conditional on winning; EIG includes every counted question, including INVALID and losses. Undefined values remain undefined.",
        "",
        "| Update | N | Reward | Wins/8 | EIG/Q | Q/win | Enum % | Invalid % | Nonzero group / cumulative % | Output tokens/game |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for r in s["updates"]:
        lines.append(
            f"| {r['update']} | {r['n']} | {num(r['mean_reward'])} | {r['wins']}/8 | {num(r['eig_per_question'])} | {num(r['questions_per_win'], 2)} | {percent(r['enumeration_rate'])} | {percent(r['invalid_question_rate'])} | {percent(r['nonzero_group_fraction'])} / {percent(r['cumulative_nonzero_group_fraction'])} | {num(r['output_tokens_per_game'], 2)} |"
        )
    signal = s["group_signal_audit"]
    lines += [
        "",
        f"Return variance occurred in {signal['nonconstant_return_groups']}/30 groups and win variance in {signal['groups_with_win_variance']}/30. Zero-win groups with cost-only return variance: {signal['zero_win_groups_with_cost_only_variance']}. Variance alone does not establish a useful win signal.",
        "",
        "## Fixed four-update development checks",
        "",
        "The same four N=4 and four N=8 training-pool cases use the same requested generation seeds at every check. They never enter gradients, but they are not held-out items or the frozen test bank. The raw control is reused without another sampling charge. Intervals resample complete games; there is one main training seed, with no between-seed uncertainty estimate.",
        "",
        "| Update | Reward | Wins/8 | EIG/Q [95% CI] | Q/win | Output tokens/game |",
        "| ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for k, d in s["development"].items():
        r = d["point"]
        lines.append(
            f"| {k} | {num(r['mean_reward'])} | {r['wins']}/8 | {interval(r['eig_per_question'], d['ci95']['eig_per_question_ci95'])} | {num(r['questions_per_win'], 2)} | {num(r['output_tokens_per_game'], 2)} |"
        )
    lines += [
        "",
        f"Raw → update 30: reward {num(base['mean_reward'])} → {num(final['mean_reward'])}, EIG/Q {num(base['eig_per_question'])} → {num(final['eig_per_question'])}, and Q/win {num(base['questions_per_win'], 2)} → {num(final['questions_per_win'], 2)}. Paired EIG change: {interval(delta['eig_per_question']['final_minus_base'], delta['eig_per_question']['ci95'])}; exact paired win p={num(delta['win_rate_exact_paired_test']['two_sided_p'])}. Small-case intervals and tests are descriptive; the frozen endpoints test larger sizes and transfer.",
        "",
        "## Guessing with k candidates remaining",
        "",
        "Each entry below is **wins / guesses**. k is measured immediately before GUESS: exact consistent support with truthful answers; the existing >0.001 plus MAP displayed list under noise. Full positive posterior support and guess confidence are also saved, since a noisy displayed singleton is not certainty. No-guess games stay in all-game denominators; no-guess is separate from k. This metric changes no reward, prompt or action restriction.",
        "",
        "| Development update | k=1 W/G | k=2 W/G | k=3 W/G | k=4+ W/G | No guess / 8 |",
        "| ---: | --- | --- | --- | --- | ---: |",
    ]
    for k, d in s["development"].items():
        g = d["point"]["guess_with_k_remaining"]
        lines.append(
            "| " + k + " | " + " | ".join(bins(g)) + f" | {g['no_guess_games']} |"
        )
    lines += [
        "",
        "| Training update | k=1 W/G | k=2 W/G | k=3 W/G | k=4+ W/G | No guess / 8 |",
        "| ---: | --- | --- | --- | --- | ---: |",
    ]
    for r in s["updates"]:
        g = r["guess_with_k_remaining"]
        lines.append(
            f"| {r['update']} | " + " | ".join(bins(g)) + f" | {g['no_guess_games']} |"
        )
    lines += [
        "",
        "## Paired frozen raw-base versus endpoint evaluation",
        "",
        "All ten cells use exactly the original indices 0–27, unchanged targets, tables and noise seeds, with separately recorded candidate-set prompt hashes. Raw base and endpoint have identical sampling settings and requested generation seeds. Every cell is reported. Bootstrap intervals use 10,000 whole-game draws, preserving policy and noise pairing; zero/all-win bootstrap intervals are supplemented by Wilson intervals in summary.json. One A seed cannot measure training-seed variation.",
        "",
        "![Paired frozen endpoint](results/main_A11/charts/frozen-endpoint.png)",
        "",
        "| Domain | N | p | Policy | Wins/28 | EIG/Q [95% CI] | Q/win [95% CI] |",
        "| --- | ---: | ---: | --- | ---: | --- | --- |",
    ]
    for r in frozen["cells"]:
        for key in ("base", "endpoint"):
            m = r[key]
            lines.append(
                f"| {r['domain']} | {r['n']} | {r['noise']:g} | {key} | {m['wins']}/28 | {interval(m['eig_per_question'], m['eig_per_question_ci95'])} | {interval(m['questions_per_win'], m['questions_per_win_ci95'])} |"
            )
    lines += [
        "",
        "The equal-cell EIG and win comparisons pool the declared cells with equal weight; they do not estimate an effect across training seeds.",
        "",
    ]
    for key, h in frozen["equal_cell_headline"].items():
        lines.append(
            f"- {key}: {num(h['base'])} → {num(h['endpoint'])}; paired change {interval(h['final_minus_base'], h['ci95'])}."
        )
    lines += [
        "",
        "| Domain | N | p | Policy | k=1 W/G | k=2 W/G | k=3 W/G | k=4+ W/G | No guess / 28 |",
        "| --- | ---: | ---: | --- | --- | --- | --- | --- | ---: |",
    ]
    for r in frozen["cells"]:
        for key in ("base", "endpoint"):
            g = r[key]["guess_with_k_remaining"]
            lines.append(
                f"| {r['domain']} | {r['n']} | {r['noise']:g} | {key} | "
                + " | ".join(bins(g))
                + f" | {g['no_guess_games']} |"
            )
    lines += [
        "",
        "Full per-cell format, invalid, truncation, enumeration, predicate-token, re-ask and cost metrics, confidence intervals and all secondary unadjusted paired p-values are in [summary.json](results/main_A11/summary.json). The noiseless ceiling is 1 bit; the p=0.10 ceiling is 0.531004 bits. The greedy baseline uses the same 28 frozen cases.",
        "",
        "## Behavior audit and limitations",
        "",
        *assessment["behavior_assessment"],
        "",
        f"Training had {train['invalid_questions']}/{train['counted_questions']} INVALID questions, {train['item_equality_questions']} item-equality questions, {train['name_list_questions']} name lists, {train['valid_zero_eig_questions']} valid zero-EIG questions and {train['post_budget_asks']} extra ASK actions rejected after budget exhaustion. No legal enumeration form was banned. All accepted predicates, answers, posteriors, EIG and rewards were replayed exactly. Malformed outputs stayed in the results; parsing exploits were audited. [Two preselected paired development games](results/main_A11/EXAMPLE_GAMES.md) include all actions and the shared tables.",
        "",
        "This is question selection with supplied state, finite authored tables and a structured grammar. Animal held-out rows share underlying animal types with training profiles. The development slice is small and easy; frozen cases were not used to select checkpoints. Only one A seed is available; B training, seed replication and hard mode are pending the next gate decision. Thinking was disabled in rendering. Visible reasoning, action and control tokens are counted separately; visible token counts do not measure internal computation.",
        "",
        "## Cost and collection",
        "",
        f"Stage usage: **${s['cost']['main_A11_spent_usd']}**, plus **${s['cost']['main_A11_held_usd']} checkpoint holds**. The forecast was ${float(proof['stage_forecast_before_margin_usd']):.6f} before margin or ${float(proof['stage_forecast_including_margin_usd']):.6f} with 1.5x margin. Recorded charges use observed tokens at the verified [provider rates](https://tinker-docs.thinkingmachines.ai/tinker/models.json), not reconciled invoices. Budget cap remains $50.",
        "",
        "| Component | Recorded usage USD |",
        "| --- | ---: |",
    ]
    for key, value in s["cost"]["sampling_by_kind_usd"].items():
        lines.append(f"| {key} sampling | {value} |")
    lines += [
        f"| Gradients | {s['cost']['gradient_usd']} |",
        "",
        f"Project usage is **${p['spent_usd']}**, holds **${p['held_usd']}**, available **${p['available_usd']}**. The nine permanently excluded historical attempts retain $0.012813; old SFT/pilot checkpoint holds remain intact. The new native endpoint and external export retain their storage holds pending billing. The adapter is downloaded locally with hashes; hosted TTL is two hours, while the downloaded export can be uploaded again for the deferred hard-mode evaluation.",
        "",
        "Execution parallelism changed from 4 to 16 after draining all 83 existing sampling requests, before any training update. Those exact outputs were reused, with no sampling resubmission. Configuration, native prompt hashes, requested seeds, sampling parameters and experiment caps did not change. Original preflight and exact prior runner source are preserved in the [execution amendment](research/main_A11_execution_amendment.json). Network recovery retains each request ID and hold; 408 means pending. All sampling and training IDs were saved before dispatch and matched to receipts or recovered results.",
        "",
        "[Validation](results/main_A11/validation.json) checks prior ledger preservation, frozen hashes, all new sampling requests and every gradient batch. [Archive-only reproduction](results/main_A11/reproduction.json) proves saved analysis works without local run caches or service calls. Source, settings, cases and optimizer parameters are pinned. No frozen game entered gradients.",
        "",
        "## Next decision",
        "",
        *assessment["next_decision"],
        "",
        "**Stopped after A seed 11. Do not start A seed 23 or B seed 41 until the user decides.**",
        "",
    ]
    (ROOT / "MAIN_A11_GATE.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
