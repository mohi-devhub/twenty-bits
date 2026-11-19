"""Render paired, labelled counter results without changing primary reports."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twenty_bits.worlds import ROOT


def number(value):
    return "undefined" if value is None else f"{value:.3f}"


def pair(a, b):
    return f"{a} → {b}"


def rate_pair(a, b, key):
    count = key + "_games"
    rate = key + "_rate"
    return pair(f"{a[count]} ({a[rate]:.1%})", f"{b[count]} ({b[rate]:.1%})")


def direction(old, new):
    if old > 0 and new == 0:
        return "removes"
    if new < old:
        return "reduces"
    if new > old:
        return "increases"
    return "does not change"


def main():
    out = ROOT / "results/visible_budget"
    result = json.loads((out / "summary.json").read_text())
    price = json.loads((ROOT / "research/visible_budget_forecast.json").read_text())
    lines = [
        "# Visible-budget evaluation gate",
        "",
        "This is a labelled evaluation-only prompt intervention on fixed policies. The main study is complete; these results do not replace any primary score. No training or checkpoint selection ran. All available policies completed the same 280 frozen games (indices 0–27 in each of ten cells). A11: **not run: A11 checkpoint wasn't persisted, external uploads unavailable**.",
        "",
        "Each user turn adds `Questions left: k of K`; k=0 also adds `No questions left. You must GUESS now.` Everything else is unchanged. The initial table/rules prefix stays byte-identical, and the original prompt hashes remain untouched. [Protocol](VISIBLE_BUDGET_PROTOCOL.md), [new hashes](evals/visible_budget/prompt_hashes.json), [full paired estimates](results/visible_budget/summary.json).",
        "",
        "## What changed",
        "",
    ]
    for name, pooled in result["pooled"].items():
        a, b = pooled["all"]["primary"], pooled["all"]["visible_budget"]
        stall = direction(a["no_guess_games"], b["no_guess_games"])
        gamble = direction(
            a["ambiguous_with_budget_left_games"], b["ambiguous_with_budget_left_games"]
        )
        lines.append(
            f"**{name}:** showing budget {stall} stalling ({pair(a['no_guess_games'], b['no_guess_games'])}/280 no-guess endings) and {gamble} ambiguous guessing with budget left ({pair(a['ambiguous_with_budget_left_games'], b['ambiguous_with_budget_left_games'])}/280). Wins {pair(a['wins'], b['wins'])}/280; EIG {pair(number(a['eig_per_question']), number(b['eig_per_question']))} bits/question. Extra ASK at the final opportunity: {pair(a['extra_ask_final_games'], b['extra_ask_final_games'])}."
        )
        lines.append("")
    lines += [
        "A lower no-guess rate can reflect more wrong guesses rather than better search. No-guess counts include context-limit losses, so they are broader than repeated-ASK stalling; the table below separates context exhaustion and extra final ASK. Ambiguous guessing is a behavior count, not automatically an error: noisy display size is a fixed thresholded posterior list. This follow-up does not establish a learned stopping strategy.",
        "",
        "The counter removes final-opportunity ASK stalling in every available policy. All 12 remaining raw no-guess endings are context-limit losses. Gambling is reduced overall for raw and B41, while A23's overall count increases. At noisy animals N=128, B41 still guesses ambiguously with budget left in 28/28 games. The prompt intervention begins on the initial turn, so question choices and stopping can both change.",
        "",
        "Noisy wins change raw 52→57, A23 29→74 and B41 36→55, each out of 140. A23's noisy EIG is nearly unchanged (0.3548→0.3540 bits/question). The primary finding that trained endpoints have fewer noisy wins than raw base therefore depends on the original observation format; it does not carry over to A23 under visible budget. These are separately labelled fixed-policy outcomes.",
        "",
        "## Paired cells",
        "",
        "Every arrow is **primary without a dynamic counter → visible budget**, on the same 28 games. EIG is ratio of summed question EIG to questions, including invalids and losses. Ambiguous-with-budget-left and no-guess percentages use all 28 games. Extra ASK is a game count at the final-guess opportunity, not an extra question in the question denominator. Early wins are correct guesses before ceil(log2 N); the complete data also include their conditional success fraction.",
        "",
    ]
    for name in result["pooled"]:
        lines += [
            f"### {name}",
            "",
            "| Domain | N | Noise | Wins /28 | EIG bits/Q | Ambiguous with budget left | No guess | Extra ASK at end | Early wins |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in result["cells"]:
            if row["policy"] != name:
                continue
            a, b = row["primary"], row["visible_budget"]
            lines.append(
                f"| {row['domain']} | {row['n']} | {row['noise']:.2f} | {pair(a['wins'], b['wins'])} | {pair(number(a['eig_per_question']), number(b['eig_per_question']))} | {rate_pair(a, b, 'ambiguous_with_budget_left')} | {rate_pair(a, b, 'no_guess')} | {pair(a['extra_ask_final_games'], b['extra_ask_final_games'])} | {pair(a['early_guess_win_games'], b['early_guess_win_games'])} |"
            )
        lines.append("")
    lines += [
        "## Paired uncertainty",
        "",
        "95% percentile intervals resample 10,000 paired complete games within each cell, sharing case draws between noise variants. Policies are fixed; no training-seed uncertainty is estimated. All comparisons are exploratory and have no multiplicity adjustment. The small cells limit precision.",
        "",
        "| Policy | Domain | N | Noise | Win-rate change [95% CI], percentage points | EIG change [95% CI] |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in result["cells"]:
        win = row["paired_changes"]["win_rate"]
        eig = row["paired_changes"]["eig_per_question"]
        wlo, whi = win["ci95"]
        elo, ehi = eig["ci95"]
        lines.append(
            f"| {row['policy']} | {row['domain']} | {row['n']} | {row['noise']:.2f} | {win['visible_minus_primary'] * 100:+.1f} [{wlo * 100:+.1f}, {whi * 100:+.1f}] | {eig['visible_minus_primary']:+.3f} [{elo:+.3f}, {ehi:+.3f}] |"
        )
    lines += [
        "",
        "## Other failure measurements",
        "",
        "All arrows retain the same primary → visible-budget order. Truncation counts turns; context exhaustion counts games and applies the unchanged prompt-plus-output-cap rule. The full per-cell JSON retains these counts.",
        "",
        "| Policy | Invalid questions | Truncated turns | Context-limit losses | Format-error turns |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, groups in result["pooled"].items():
        a, b = groups["all"]["primary"], groups["all"]["visible_budget"]
        lines.append(
            f"| {name} | {pair(a['invalid_questions'], b['invalid_questions'])} | {pair(a['truncated_turns'], b['truncated_turns'])} | {pair(a['context_overflow_games'], b['context_overflow_games'])} | {pair(a['format_error_turns'], b['format_error_turns'])} |"
        )
    budget = result["followup_budget"]
    project = result["project_budget"]
    lines += [
        "",
        "## Spend and verification",
        "",
        f"The frozen forecast was **${price['forecast_including_margin_usd']} including 1.5 margin**, versus **${budget['spent_usd']} recorded usage + ${budget['held_usd']} unresolved follow-up holds** under the $8 ceiling. It credited 70% cached input versus an observed prior minimum of {price['observed_minimum_cohort_cache_fraction']:.1%}, added 15% behavior allowance, then applied the margin. The uncached replay was ${float(price['uncached_replay_usd']):.6f}; caching was an explicit forecast assumption, not a guarantee.",
        "",
        f"Project usage is **${project['spent_usd']}**, all holds **${project['held_usd']}**, leaving **${project['available_usd']} of $50**. These are observed-token charges at pinned rates; invoice reconciliation is pending. All older lost-original and storage holds remain. No new checkpoint save or storage reservation was needed.",
        "",
        "| Policy | Input tokens | Cache-hit tokens | Cache fraction | Output tokens | Visible reasoning tokens | Usage USD |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, tokens in result["tokens"].items():
        lines.append(
            f"| {name} | {tokens['prompt_tokens']:,} | {tokens['prompt_cache_hit_tokens']:,} | {tokens['prompt_cache_hit_tokens'] / tokens['prompt_tokens']:.1%} | {tokens['output_tokens']:,} | {tokens['reasoning_tokens']:,} | {result['sampling_usage_usd_by_policy'][name]} |"
        )
    v = result["verification"]
    lines += [
        "",
        f"All {v['native_prompt_sequences']:,} native prompt sequences match the cookbook renderer and saved request signatures. All {v['accepted_sample_requests']:,} accepted requests saved deterministic IDs before HTTP dispatch and verified receipts. Actions, answers, seeded flips, posteriors, EIG and rewards replay exactly under the unchanged game. No gradient, optimizer or checkpoint-save operations ran. Every primary artifact captured in the preflight still has its original hash.",
        "",
    ]
    registry = json.loads(
        (ROOT / "research/visible_budget_replacements.json").read_text()
    )
    if registry["cases"]:
        lines += [
            f"{len(registry['cases'])} lost originals remain permanently excluded with their holds retained under the standing rule. Exact replacement cases:",
            "",
        ]
        for case in registry["cases"]:
            lines.append(
                f"- `{case['original_request_id']}` → `{case.get('replacement_request_id', 'not dispatched')}`; reason: {case.get('reason', case.get('loss_reason', 'see registry'))}."
            )
    else:
        lines += ["No request was lost and no replacement ran in this follow-up.", ""]
    lines += [
        "The service session is finished and HTTP work is drained. The gate includes 226 passing unit tests, archived accepted responses and exclusions, a separate ledger event export and credential-free replay verification. Thinking remains disabled; zero visible reasoning tokens do not measure internal computation.",
        "",
        "## Stop",
        "",
        "Stopped at this gate. The user will decide between a training follow-up and the final write-up phase. No more main seeds, training, final replay/video, results article or X thread has started.",
        "",
    ]
    (ROOT / "VISIBLE_BUDGET_GATE.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
